"""GM-003 v1: server-side GM command grammar -- PARSE AND LOG ONLY.

Scope of this file, stated plainly so it cannot be over-claimed later:

* It parses the six command strings the owner asked for (``warp`` ``npc``
  ``item`` ``lv`` ``spawn`` ``say``) into a structured ``GmCommand``.
* It logs an issued command server-side (``log_gm_command``).
* It does **not** execute any of them.  Executing ``warp``/``spawn`` needs
  ``TeleportVital``/``ForcePos``/mob-spawn wiring that is not proven yet
  (notes_to_chief 20260826_1630 lists these as RE-open); executing
  ``npc``/``item``/``lv`` needs write access to player/world state that
  lives in runtime.py, outside this lane's write zone.  Wiring any of that
  in is a CORE-REQUEST to chief, filed per command once its dependency is
  ready -- see docs/GM_LANE.md.
* ``GM_RunGMCommandVital`` (0x51E9, client->server) is how a real client
  would deliver this text, but that message's own field layout is also not
  proven yet (see ``gm/command_capture.py``, GM-002).  This module therefore
  takes a plain ``str`` and does not depend on 0x51E9 at all, so command
  parsing/logging can be exercised and tested before that capture lands.

``warp``'s scene_id is checked against ``gm.scene_catalog`` (GM-004, this
lane's own committed catalog) only to flag a scene_id that has no known GM
name -- it is a hint for the log, not a hard rule, because a scene_id
missing from the catalog is not proof that warping there is invalid.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import time
from pathlib import Path

from . import scene_catalog

COMMAND_NAMES = ("warp", "npc", "item", "lv", "spawn", "say")

DEFAULT_LOG_PATH = "capture/gm_command_log.ndjson"


@dataclass(frozen=True)
class GmCommand:
    name: str
    args: tuple[str, ...]
    raw: str


class GmCommandParseError(ValueError):
    pass


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
        float(value)
    except ValueError as exc:
        raise GmCommandParseError(f"{label} must be a number, got {value!r}") from exc


def describe_warp_target(command: GmCommand) -> str | None:
    """The GM scene name for a parsed warp command's scene_id, or None if
    the id has no row in the GM-004 catalog -- a hint, not a validity gate.
    """
    if command.name != "warp":
        raise ValueError("describe_warp_target only applies to warp commands")
    scene_id = int(command.args[0])
    if not scene_catalog.is_known_scene_id(scene_id):
        return None
    return scene_catalog.gm_scene_name(scene_id)


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
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = now_ts if now_ts is not None else time.time()
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        "account": account_name,
        "command": command.name,
        "args": list(command.args),
        "raw": command.raw,
        "executed": False,
        "note": "GM-003 v1: parsed and logged only, no gameplay effect applied",
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path
