"""SAME-SLOT-NOOP-001 headless probe: same-slot move no-op, replay-safe.

HYP-PF-010 already accepts that a same-slot ItemOperate move is a silent
no-op with no write.  The occupied-destination swap probe (ITEM-SWAP-001,
scenario D) proved same-slot silence once under the swap profile.  This probe
locks the ``same_slot_noop`` capability under the *default* free-slot profile
(scenarios/item_move_hypothesis_v111_slot2.json) and adds the replay dimension
the coverage note requires: no response, no write, and no replay side-effect.

Against a real server process over real TCP with a scratch DB only:

  server (default free-slot profile, second scratch DB):
    For each of three same-slot targets -- identity 1 at slot 0, identity 2
    at slot 1, identity 4 at slot 3 of the initial four-item Backpack -- send
    the exact same-slot ItemOperate request three times on one connection.
    Every send must produce zero non-heartbeat frames, and the two
    persistence tables (character_backpack_items rows and
    character_backpacks.updated_at) must be byte-identical before the first
    send and after the last replay.

Scope guard: sockets + one scratch DB only.  Never launches, touches, or
automates GameClient.  Never opens the canonical state DB.  No repo writes
(--json and --db-file must point outside the repo).  stdlib only.

Exit codes
  0  all passes held
  3  ran, but at least one expectation failed (details in JSON)
  4  socket/connection problem
  2  usage problem
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import socket
import sqlite3
import struct
import subprocess
import sys
import time
from pathlib import Path


HEARTBEAT_FRAME_SHA256 = (
    "B4F6CFA26FF6181AD62E57BFA8B6813368F24FCF31E69E4FBFAE6E0AE452ACB1"
)


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest().upper()


def _load_legacy(root: Path):
    path = root / "current" / "pf_login_game_server_v141.py"
    spec = importlib.util.spec_from_file_location("pf_probe_legacy_v141", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def recv_frame(sock: socket.socket) -> bytes | None:
    head = b""
    while len(head) < 8:
        chunk = sock.recv(8 - len(head))
        if not chunk:
            return None
        head += chunk
    _magic, nlen = struct.unpack("<II", head)
    body = b""
    while len(body) < nlen:
        chunk = sock.recv(nlen - len(body))
        if not chunk:
            return None
        body += chunk
    return head + body


def drain(sock, seconds):
    frames: list[tuple[float, bytes]] = []
    deadline = time.monotonic() + seconds
    while True:
        remain = deadline - time.monotonic()
        if remain <= 0:
            return frames, False
        sock.settimeout(remain)
        try:
            frame = recv_frame(sock)
        except socket.timeout:
            return frames, False
        except OSError:
            return frames, True
        if frame is None:
            return frames, True
        frames.append((time.time(), frame))


def non_heartbeats(stamped):
    return [(t, b) for t, b in stamped if _sha(b) != HEARTBEAT_FRAME_SHA256]


def backpack_rows(db_path: Path):
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return [
            tuple(row) for row in db.execute(
                "SELECT item_identity, slot, quantity, template_id "
                "FROM character_backpack_items ORDER BY item_identity"
            ).fetchall()
        ]
    finally:
        db.close()


def backpack_updated_at(db_path: Path):
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = db.execute(
            "SELECT updated_at FROM character_backpacks LIMIT 1"
        ).fetchone()
        return row[0] if row else None
    finally:
        db.close()


def enter_runtime_ready(legacy, host, port, db_path, window, checks, tag):
    s = socket.create_connection((host, port), timeout=8.0)
    s.sendall(legacy.frame_pc(legacy._synthetic_client_login_pc()))
    drain(s, window)

    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        actives = db.execute(
            "SELECT selector FROM characters WHERE deleted_at IS NULL"
        ).fetchall()
    finally:
        db.close()
    if not actives:
        s.sendall(legacy.frame_pc(legacy._V25_REAL_CREATE_PC))
        drain(s, window)
        db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            actives = db.execute(
                "SELECT selector FROM characters WHERE deleted_at IS NULL"
            ).fetchall()
        finally:
            db.close()
    selector = int(actives[0][0])

    s.sendall(legacy.frame_pc(legacy._synthetic_start_game_pc(selector)))
    drain(s, window)
    s.sendall(legacy.frame_pc(legacy.V136_EMPTY_RUNTIME_REQ_PC))
    drain(s, window)
    frames, _eof = drain(s, 2.6)
    checks[f"{tag}_heartbeats_before_request"] = len(frames) - len(
        non_heartbeats(frames)
    )
    return s


def same_slot_replay_pass(legacy, request_pc, args, db_path, checks, tag,
                          *, repeats):
    """One connection: replay a same-slot request; True iff every send silent
    and neither persistence table moved from first read to last."""
    ok = True
    s = enter_runtime_ready(
        legacy, args.host, args.game_port, db_path, args.window, checks, tag,
    )
    try:
        before_rows = backpack_rows(db_path)
        before_updated = backpack_updated_at(db_path)
        sends = []
        for _ in range(repeats):
            s.sendall(legacy.frame_pc(request_pc))
            stamped, eof = drain(s, args.window)
            others = non_heartbeats(stamped)
            silent = (not eof) and (not others)
            sends.append({
                "silent_no_reply": bool(silent),
                "eof": bool(eof),
                "non_heartbeat_frames": [
                    {"bytes": len(b), "sha256": _sha(b)} for _t, b in others
                ],
            })
            ok = ok and silent
        after_rows = backpack_rows(db_path)
        after_updated = backpack_updated_at(db_path)
        no_write = (
            after_rows == before_rows and after_updated == before_updated
        )
        checks[f"{tag}_sends"] = sends
        checks[f"{tag}_rows_before"] = before_rows
        checks[f"{tag}_rows_after"] = after_rows
        checks[f"{tag}_updated_at_before"] = before_updated
        checks[f"{tag}_updated_at_after"] = after_updated
        checks[f"{tag}_no_write_across_replays"] = bool(no_write)
        ok = ok and no_write
        checks[f"{tag}_ok"] = bool(ok)
        return ok
    finally:
        try:
            s.close()
        except OSError:
            pass


def boot_server(root, db_path, scenario_rel, host, port, boot_wait):
    server = subprocess.Popen(
        [sys.executable, "-m", "pirateforce_foundation.app",
         "--db", str(db_path),
         "--item-move-hypothesis-scenario", str(root / scenario_rel)],
        cwd=root, env={**__import__("os").environ,
                       "PYTHONPATH": str(root / "src")},
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )
    deadline = time.monotonic() + boot_wait
    while time.monotonic() < deadline:
        try:
            socket.create_connection((host, port), timeout=0.5).close()
            return server
        except OSError:
            time.sleep(0.4)
    server.terminate()
    return None


def stop_server(server):
    if server is None:
        return
    server.terminate()
    try:
        server.wait(timeout=10)
    except subprocess.TimeoutExpired:
        server.kill()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--game-port", type=int, default=10189)
    ap.add_argument("--db-file", required=True,
                    help="scratch DB for the default-profile server, OUTSIDE "
                         "the repo; must exist (migrated) before boot")
    ap.add_argument("--json", required=True)
    ap.add_argument("--window", type=float, default=2.0)
    ap.add_argument("--boot-wait", type=float, default=15.0)
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    db_default = Path(args.db_file).resolve()
    if not db_default.is_file():
        print(f"scratch DB missing: {db_default}", file=sys.stderr)
        return 2
    for target in (db_default, Path(args.json).resolve()):
        try:
            target.relative_to(root)
        except ValueError:
            continue
        print(f"refusing repo write target: {target}", file=sys.stderr)
        return 2

    legacy = _load_legacy(root)
    sys.path.insert(0, str(root / "src"))
    from pirateforce_foundation.inventory import (  # noqa: E402
        INITIAL_BACKPACK,
        move_known_item_to_free_slot,
    )
    from pirateforce_foundation.item_move_capture import (  # noqa: E402
        ITEM_MOVE_CAPTURE_REQUEST_PC,
    )

    def request_pc(destination_slot: int, item_identity: int) -> bytes:
        pc = (
            ITEM_MOVE_CAPTURE_REQUEST_PC[:23]
            + struct.pack("<I", destination_slot)
            + ITEM_MOVE_CAPTURE_REQUEST_PC[27:28]
            + struct.pack("<Q", item_identity)
        )
        assert len(pc) == len(ITEM_MOVE_CAPTURE_REQUEST_PC)
        return pc

    # Each target must be that item's own slot in the initial four-item bag,
    # so the pure transition returns the exact same-slot None before we ever
    # touch the wire.
    targets = [(0, 1), (1, 2), (3, 4)]
    for destination_slot, item_identity in targets:
        assert move_known_item_to_free_slot(
            INITIAL_BACKPACK, item_identity, destination_slot,
        ) is None

    verdict: dict = {"probe": "SAME-SLOT-NOOP-001", "checks": {}, "ok": False}
    checks = verdict["checks"]
    checks["targets"] = [
        {"item_identity": i, "own_slot": s} for s, i in targets
    ]
    checks["repeats_per_target"] = args.repeats

    server = boot_server(
        root, db_default, "scenarios/item_move_hypothesis_v111_slot2.json",
        args.host, args.game_port, args.boot_wait,
    )
    if server is None:
        print("default-profile server did not open the GAME port",
              file=sys.stderr)
        return 4
    results = []
    try:
        for idx, (destination_slot, item_identity) in enumerate(targets):
            tag = f"t{idx}_id{item_identity}_slot{destination_slot}"
            ok = same_slot_replay_pass(
                legacy, request_pc(destination_slot, item_identity),
                args, db_default, checks, tag, repeats=args.repeats,
            )
            results.append(ok)
            time.sleep(1.0)
    except (OSError, socket.timeout) as exc:
        verdict["error"] = repr(exc)
        Path(args.json).write_text(json.dumps(verdict, indent=1),
                                   encoding="utf-8")
        print(json.dumps(verdict, indent=1))
        stop_server(server)
        return 4
    finally:
        stop_server(server)

    heartbeat_ok = all(
        checks.get(f"t{idx}_id{i}_slot{s}_heartbeats_before_request", 0) >= 1
        for idx, (s, i) in enumerate(targets)
    )
    checks["heartbeat_seen_before_every_request"] = heartbeat_ok
    verdict["ok"] = bool(all(results) and heartbeat_ok)
    code = 0 if verdict["ok"] else 3
    Path(args.json).write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    print(json.dumps(verdict, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
