#!/usr/bin/env python3
"""DELETE-REFRESH-001: headless wire/DB proof of the HYP-PF-021 list rebuild.

Attended GT-011 ended with the soft delete committed, no error dialog, and the
character-select list not moving.  UI-REFRESH-001 proved from the client image
that no acknowledgement can ever remove a row -- the list has one buffer and no
erase-by-key path -- and that the only frame that can is a fresh
``SelectActorVital`` 0x36EF.  HYP-PF-021 sends exactly that after the pinned
0x36DB echo ack.  This replay proves the server half of it over real TCP,
before any human is asked to look at a screen.

What is driven, on a real server process over real sockets and a SCRATCH DB:

  connection A   login_verify -> character list -> create (the real captured
                 V25 create PC) -> the designed DeleteActorVital op-1 request
    1. EXACTLY TWO non-heartbeat frames come back, in this order:
         [0] the unchanged, hash-pinned HYP-PF-015 echo ack (44-byte frame)
         [1] the SelectActorVital 0x36EF list rebuild (55-byte frame for the
             empty post-delete list, hash-pinned)
    2. the rebuild decompresses and re-parses to nested id 0x36EF, nested
       version 10, and a record-count byte of 0 -- i.e. the character really
       is gone from the frame the client will rebuild its list from
    3. the rebuild carries the DELETE-SOFT-002 trailing derived-class change
       mask (the byte whose absence gave GT-010 ErrorData=28317)
    4. the DB shows deleted_at set, the active list empty, and the child
       position/backpack rows surviving as history
    5. an op-2 request afterwards produces no reply and no write (fail closed)
  connection B   login_verify -> the designed op-1 request with nothing to
                 delete
    6. no reply and no write at all (the repository refusal is silent)

Scope guard: sockets and a scratch DB only.  Never launches, touches or
automates GameClient.  Never opens the canonical state DB.  Refuses to write
anything inside the repository.  stdlib only.

    py -3 tools\\pf_delete_refresh001_headless_replay.py ^
        --config tools\\pf_delete_refresh001_headless_replay_config.json ^
        --db-file C:\\Temp\\pf_delete_refresh001\\state.sqlite3 ^
        --json C:\\Temp\\pf_delete_refresh001\\verdict.json

The scratch DB must exist and be migrated before the server boots; pass
``--prepare-db`` to have this script create and migrate it for you.

Exit codes
  0  the full ack-then-rebuild sequence held
  3  ran, but at least one expectation failed (details in the verdict JSON)
  4  socket/connection problem
  2  usage problem
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
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
DEFAULT_CONFIG = (
    Path(__file__).resolve().parent
    / "pf_delete_refresh001_headless_replay_config.json"
)


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest().upper()


def _load_legacy(root: Path):
    path = root / "current" / "pf_login_game_server_v141.py"
    spec = importlib.util.spec_from_file_location("pf_replay_legacy_v141", path)
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


def drain(sock: socket.socket, seconds: float) -> list[bytes]:
    frames: list[bytes] = []
    deadline = time.monotonic() + seconds
    while True:
        remain = deadline - time.monotonic()
        if remain <= 0:
            return frames
        sock.settimeout(remain)
        try:
            frame = recv_frame(sock)
        except socket.timeout:
            return frames
        if frame is None:
            return frames
        frames.append(frame)


def non_heartbeats(frames: list[bytes]) -> list[bytes]:
    return [b for b in frames if _sha(b) != HEARTBEAT_FRAME_SHA256]


def db_rows(db_path: Path) -> list[tuple]:
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return db.execute(
            "SELECT id,selector,identity_lo,identity_hi,create_fingerprint,"
            "deleted_at FROM characters ORDER BY id"
        ).fetchall()
    finally:
        db.close()


def db_children(db_path: Path) -> tuple[int, int]:
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        positions = db.execute(
            "SELECT COUNT(*) FROM character_positions"
        ).fetchone()[0]
        items = db.execute(
            "SELECT COUNT(*) FROM character_backpack_items"
        ).fetchone()[0]
        return positions, items
    finally:
        db.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=str(DEFAULT_CONFIG),
                    help="replay config JSON (defaults to the sibling file)")
    ap.add_argument("--root", help="Pirate Force ServerProject checkout root")
    ap.add_argument("--host")
    ap.add_argument("--game-port", type=int)
    ap.add_argument("--db-file", required=True,
                    help="scratch DB path OUTSIDE the repo")
    ap.add_argument("--json", required=True,
                    help="verdict JSON path OUTSIDE the repo")
    ap.add_argument("--capture-root",
                    help="where the booted server writes packet captures; must "
                         "be OUTSIDE the repo. Defaults to <db-file dir>/capture. "
                         "Never let this fall back to the cwd: the repo root's "
                         "capture_v141/ is pinned read-only evidence.")
    ap.add_argument("--window", type=float)
    ap.add_argument("--boot-wait", type=float)
    ap.add_argument("--prepare-db", action="store_true",
                    help="create and migrate the scratch DB before booting")
    ap.add_argument("--no-server", action="store_true",
                    help="attach to an already-running server instead of "
                         "booting one")
    args = ap.parse_args()

    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"unreadable config: {exc}", file=sys.stderr)
        return 2
    if config.get("schema") != 1 or config.get("hypothesis") != "HYP-PF-021":
        print("config is not a DELETE-REFRESH-001 replay config", file=sys.stderr)
        return 2

    here = Path(__file__).resolve().parents[1]
    root = Path(args.root or config.get("root") or here).resolve()
    host = args.host or config["host"]
    game_port = args.game_port or config["game_port"]
    window = args.window if args.window is not None else config["window_seconds"]
    boot_wait = (
        args.boot_wait if args.boot_wait is not None
        else config["boot_wait_seconds"]
    )
    scenario_path = root / config["scenario"]
    if not scenario_path.is_file():
        print(f"scenario missing: {scenario_path}", file=sys.stderr)
        return 2

    db_path = Path(args.db_file).resolve()
    json_path = Path(args.json).resolve()

    # The server writes its packet captures into the CURRENT DIRECTORY unless it is
    # given --capture-root, and this script runs it with cwd=root.  Round 81 learned
    # what that costs: the first gate run of this replay dropped three fresh capture
    # files straight into capture_v141/, the pinned read-only golden corpus, which
    # grew 69 -> 72 files and broke an unrelated milestone's pinned count (44 -> 46).
    # capture_v141/ is gitignored, so git showed nothing and no guard fired.  The
    # capture root is therefore mandatory here, it lives beside the scratch DB, and
    # anything that resolves inside the repo is refused before a socket is opened.
    capture_root = (
        Path(args.capture_root).resolve() if args.capture_root
        else db_path.parent / "capture"
    )
    for target in (db_path, json_path, capture_root):
        try:
            target.relative_to(root)
        except ValueError:
            continue
        print(f"refusing repo write target: {target}", file=sys.stderr)
        return 2
    capture_root.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(root / "src"))
    legacy = _load_legacy(root)
    from pirateforce_foundation.delete_actor_hypothesis import (  # noqa: E402
        DELETE_ACTOR_PROBE_ACK_FRAME_SHA256,
        DELETE_ACTOR_PROBE_NESTED_PAYLOADS,
        _login_protocol_request_pc,
    )
    from pirateforce_foundation.delete_refresh_hypothesis import (  # noqa: E402
        LIST_REBUILD_EMPTY_FRAME_SHA256,
        LIST_REBUILD_EMPTY_PC_SHA256,
        LIST_REBUILD_PAYLOAD_SUFFIX,
        LIST_REBUILD_PC_HEADER_SIZE,
        SELECT_ACTOR_VITAL_ID,
        SELECT_ACTOR_VITAL_VERSION,
    )

    if args.prepare_db:
        from pirateforce_foundation.store import SQLiteStore  # noqa: E402
        db_path.parent.mkdir(parents=True, exist_ok=True)
        SQLiteStore(db_path, root / "migrations").migrate()
    if not db_path.is_file():
        print(f"scratch DB missing: {db_path}", file=sys.stderr)
        return 2

    delete_pc = _login_protocol_request_pc(
        legacy, DELETE_ACTOR_PROBE_NESTED_PAYLOADS["op1_selector0_empty"],
    )
    op2_pc = _login_protocol_request_pc(
        legacy, bytes.fromhex("0802080014000000004400000000"),
    )
    ack_pin = DELETE_ACTOR_PROBE_ACK_FRAME_SHA256["op1_selector0_empty"]

    verdict: dict = {
        "probe": "DELETE-REFRESH-001",
        "hypothesis": "HYP-PF-021",
        "scenario": config["scenario"],
        "checks": {},
        "ok": False,
    }
    checks = verdict["checks"]

    server = None
    if not args.no_server:
        server = subprocess.Popen(
            [sys.executable, "-m", "pirateforce_foundation.app",
             "--db", str(db_path),
             "--capture-root", str(capture_root),
             "--delete-refresh-hypothesis-scenario", str(scenario_path)],
            cwd=root, env={**os.environ, "PYTHONPATH": str(root / "src")},
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + boot_wait
        while time.monotonic() < deadline:
            try:
                socket.create_connection((host, game_port), timeout=0.5).close()
                break
            except OSError:
                time.sleep(0.4)
        else:
            print("server did not open the GAME port", file=sys.stderr)
            server.terminate()
            return 4

    code = 3
    try:
        # ---- connection A -------------------------------------------------
        a = socket.create_connection((host, game_port), timeout=8.0)
        a.sendall(legacy.frame_pc(legacy._synthetic_client_login_pc()))
        checks["a_login_reply_frames"] = len(non_heartbeats(drain(a, window)))

        rows = db_rows(db_path)
        if not [r for r in rows if r[5] is None]:
            a.sendall(legacy.frame_pc(legacy._V25_REAL_CREATE_PC))
            checks["a_create_reply_frames"] = len(
                non_heartbeats(drain(a, window))
            )
            rows = db_rows(db_path)
        active = [r for r in rows if r[5] is None]
        checks["a_active_before_delete"] = len(active)
        if len(active) != 1 or active[0][1] != 0:
            raise AssertionError("expected exactly one active selector-0 row")
        original = active[0]
        children_before = db_children(db_path)

        # ---- the claim ----------------------------------------------------
        a.sendall(legacy.frame_pc(delete_pc))
        replies = non_heartbeats(drain(a, window))
        checks["delete_reply_frames"] = len(replies)
        checks["delete_reply_is_ack_then_rebuild"] = bool(
            len(replies) == 2
            and _sha(replies[0]) == ack_pin
            and _sha(replies[1]) == LIST_REBUILD_EMPTY_FRAME_SHA256
        )
        if len(replies) == 2:
            checks["ack_frame_sha256"] = _sha(replies[0])
            checks["rebuild_frame_sha256"] = _sha(replies[1])
            rebuild_pc = legacy.snappy_raw_decompress(replies[1][8:])
            checks["rebuild_pc_sha256"] = _sha(rebuild_pc)
            checks["rebuild_pc_matches_pin"] = bool(
                _sha(rebuild_pc) == LIST_REBUILD_EMPTY_PC_SHA256
            )
            parsed = legacy.parse_outer(rebuild_pc)
            checks["rebuild_nested_id"] = "0x%04X" % parsed.nested_id
            checks["rebuild_nested_version"] = parsed.nested_version
            checks["rebuild_is_select_actor_v10"] = bool(
                parsed.nested_id == SELECT_ACTOR_VITAL_ID
                and parsed.nested_version == SELECT_ACTOR_VITAL_VERSION
            )
            payload = rebuild_pc[LIST_REBUILD_PC_HEADER_SIZE:]
            # payload prefix: 0B 00 | 14 x4 0 | 14 x4 0 | 1F x4 0 | 0B 00 |
            #                 0B <record count>
            checks["rebuild_record_count"] = payload[20]
            checks["rebuild_lists_no_characters"] = bool(payload[20] == 0)
            checks["rebuild_carries_trailing_derived_class_mask"] = bool(
                payload.endswith(LIST_REBUILD_PAYLOAD_SUFFIX)
            )

        rows = db_rows(db_path)
        deleted = [r for r in rows if r[0] == original[0]][0]
        checks["deleted_at_set"] = deleted[5] is not None
        checks["active_after_delete"] = len([r for r in rows if r[5] is None])
        checks["children_survive"] = db_children(db_path) == children_before

        # ---- fail-closed negatives ---------------------------------------
        a.sendall(legacy.frame_pc(op2_pc))
        checks["op2_reply_frames"] = len(non_heartbeats(drain(a, window)))
        checks["op2_no_write"] = db_rows(db_path) == rows
        a.close()

        b = socket.create_connection((host, game_port), timeout=8.0)
        b.sendall(legacy.frame_pc(legacy._synthetic_client_login_pc()))
        drain(b, window)
        b.sendall(legacy.frame_pc(delete_pc))
        checks["b_nothing_to_delete_reply_frames"] = len(
            non_heartbeats(drain(b, window))
        )
        checks["b_no_write"] = db_rows(db_path) == rows
        b.close()

        verdict["ok"] = bool(
            checks["delete_reply_is_ack_then_rebuild"]
            and checks.get("rebuild_pc_matches_pin")
            and checks.get("rebuild_is_select_actor_v10")
            and checks.get("rebuild_lists_no_characters")
            and checks.get("rebuild_carries_trailing_derived_class_mask")
            and checks["deleted_at_set"]
            and checks["active_after_delete"] == 0
            and checks["children_survive"]
            and checks["op2_reply_frames"] == 0
            and checks["op2_no_write"]
            and checks["b_nothing_to_delete_reply_frames"] == 0
            and checks["b_no_write"]
        )
        code = 0 if verdict["ok"] else 3
    except (OSError, socket.timeout) as exc:
        verdict["error"] = repr(exc)
        code = 4
    except AssertionError as exc:
        verdict["error"] = repr(exc)
        code = 3
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(verdict, indent=1), encoding="utf-8")
        print(json.dumps(verdict, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
