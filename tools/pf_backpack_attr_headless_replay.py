#!/usr/bin/env python3
"""RE-305 precondition: what the StartGame BackpackAttr actually carries.

WHY THIS FILE EXISTS.  `PANYA-ORDER 20260907_0159` says an attended ticket
without a `HEADLESS_PROOF:` token does not board the capture bus, and
`COO-DECISION 20260907_2148` ruled what that token means for a ticket that
reads the CLIENT's own memory (`RE-305`): not "the server answers op=5" --
it does not, and the ticket never asked it to -- but the PRECONDITION the
tester needs on screen, which is that THE ITEM THEY ARE TOLD TO DRAG IS IN
THE BAG.  That precondition is server-sent: the StartGame reply carries the
BackpackAttr.  This file measures it.

WHAT IT PROVES, AND WHERE THE PROOF STOPS.  It boots the REAL foundation
login path -- `SQLiteStore.migrate` on a throwaway file, `create`, then
`FoundationSession.select_and_start` -- and reads the template ids back out
of the composed StartGame frame by WALKING THE BYTES, not by asking the
composer what it composed.  It then checks that those exact BackpackAttr
bytes are a substring of the StartGame frame the session queued, which is
what makes the sentence "the server sends them" true rather than "the
server could compose them".

It proves NOTHING about a client.  No client is booted, no socket is
opened, no window appears.  Whether the item is DRAGGABLE, what the client
writes into `ItemAttr+0x39` when it is dragged, and whether `value32`
carries the slot bit are the whole of `RE-305` and are exactly what this
file cannot answer.

DISCIPLINE.  No server process, no socket, no network, no GameClient.  A
temporary directory holds the only database this file opens, and it is
deleted on exit.  No repository file is written.

Usage:
    python3 tools/pf_backpack_attr_headless_replay.py
    python3 tools/pf_backpack_attr_headless_replay.py --json

Exit 0 = the frame carried the composed BackpackAttr and the walk agreed
with the loaded rows.  Exit 1 = it did not.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.inventory import make_backpack_attr  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector,
    load_legacy,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.session import FoundationSession  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
TOKEN = "RE305_BACKPACK_ATTR_SENT"


def _walk_templates(blob: bytes) -> list[int]:
    """Read the template ids out of a BackpackAttr body, byte by byte.

    Deliberately does NOT import the composer's own helpers: a reader that
    calls the writer's functions proves the two agree with themselves.  The
    layout walked here is the one `inventory.make_backpack_attr` lays down
    -- u8tag(0x0B) base mask, qwordtag(0x32) base identity, u16tag(0x0F)
    count, then per item qword identity, u32 template, u16 quantity, u16
    slot, u8 raw_38, u8 raw_39, u8 detail.  Each tag is one type byte
    followed by its payload.
    """
    def take(view: memoryview, tag: int, width: int) -> tuple[int, memoryview]:
        if not view or view[0] != tag:
            raise ValueError(f"expected tag 0x{tag:02X}, saw {bytes(view[:1])!r}")
        payload = bytes(view[1:1 + width])
        if len(payload) != width:
            raise ValueError("truncated BackpackAttr body")
        return int.from_bytes(payload, "little"), view[1 + width:]

    view = memoryview(blob)
    _base_mask, view = take(view, 0x0B, 1)
    _base_identity, view = take(view, 0x32, 8)
    count, view = take(view, 0x0F, 2)
    templates: list[int] = []
    for _ in range(count):
        _identity, view = take(view, 0x32, 8)
        template, view = take(view, 0x14, 4)
        _quantity, view = take(view, 0x0F, 2)
        _slot, view = take(view, 0x0F, 2)
        _raw38, view = take(view, 0x08, 1)
        _raw39, view = take(view, 0x08, 1)
        _detail, view = take(view, 0x0B, 1)
        templates.append(template)
    return templates


def _head_commit() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001 - provenance is best effort, never fatal
        return "unknown"


def run() -> dict:
    legacy = load_legacy(LEGACY_PATH)
    with tempfile.TemporaryDirectory() as tmp:
        store = SQLiteStore(Path(tmp) / "state.sqlite3", ROOT / "migrations")
        store.migrate()
        home = Position(
            1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
            legacy.V135_PLAYER_Z,
        )
        lifecycle = CharacterLifecycle(
            store, home, legacy.extract_avatar_attr_wire_from_actor,
        )
        session = FoundationSession(
            lifecycle, LegacyProjector(legacy), "re305-headless",
        )
        character, _ = session.create(
            "test01", legacy.get_preset_actor_wire(),
        )
        _selected, (start_pc, _frame) = session.select_and_start(
            character.selector,
        )
        # `start_pc` is the byte string the client parses -- the same value
        # `tests/test_persistence_backpack_relogin.py` counts the composed
        # bag inside.  `session.backpack` is what `session.py` loaded for
        # this login, not a value asked of the store afterwards.
        start_frame = start_pc
        composed = make_backpack_attr(legacy, session.backpack)
        walked = _walk_templates(composed)
        loaded = [item.template_id for item in session.backpack.items]
        return {
            "commit": _head_commit(),
            "in_start_game_frame": composed in start_frame,
            "start_game_frame_bytes": len(start_frame),
            "backpack_attr_bytes": len(composed),
            "templates_walked_from_the_wire": walked,
            "templates_in_the_loaded_rows": loaded,
            "walk_agrees_with_rows": walked == loaded,
            "worn_bytes_raw_u8_39": [
                item.raw_u8_39 for item in session.backpack.items
            ],
            "occurrences_in_start_game_frame": start_frame.count(composed),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run()
    ok = result["in_start_game_frame"] and result["walk_agrees_with_rows"]
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"{TOKEN} commit={result['commit']} "
            f"templates={','.join(str(t) for t in result['templates_walked_from_the_wire'])} "
            f"worn_u8_39={','.join(str(w) for w in result['worn_bytes_raw_u8_39'])} "
            f"in_start_game_frame={str(result['in_start_game_frame']).lower()} "
            f"frame_bytes={result['start_game_frame_bytes']}"
        )
        if not ok:
            print("!! the composed BackpackAttr is NOT in the StartGame frame")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
