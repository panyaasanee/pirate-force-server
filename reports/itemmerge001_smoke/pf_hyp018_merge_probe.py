"""HYP-PF-018 headless probe: occupied-destination same-template merge, ITEM-MERGE-001.

Against real server processes over real TCP with scratch DBs only:

  server 1 (merge profile, scenarios/item_move_hypothesis_v111_occupied_merge.json,
      first scratch DB):
    pass A: runtime-ready -> ItemOperate move id3 -> occupied slot0
      (same template 2600001) -> exactly one non-heartbeat frame, byte-equal
      to the FROZEN V141 GOLDEN the real client accepted at V111 runtime
      (surviving id1 quantity 2 at slot 0, removal collection naming id3),
      and both persistence tables record the merge: character_backpack_items
      rows [(1,0,2),(2,1,1),(4,3,1)] and character_backpacks.updated_at
      advanced
  server 2 (merge profile, second scratch DB):
    pass B: free-slot regression under the merge profile (id1 -> free slot7)
      -> the unchanged HYP-PF-010 single-item delta pin
    pass C: generalized merge at the relocated target (id3 -> occupied
      slot7) -> one frame byte-equal to the composed merge-delta pin
      (surviving id1 quantity 2 at slot 7; same structure as the golden,
      different bytes), rows [(1,7,2),(2,1,1),(4,3,1)]
    pass D: different-template occupied (id4 -> slot1, occupied by id2)
      -> silence, no write (fail closed under the merge profile)
    pass E: same-slot no-op (id2 -> slot1) -> silence, no write
  server 3 (original move profile, scenarios/item_move_hypothesis_v111_slot2.json,
      third scratch DB):
    pass F: occupied same-template request (id3 -> slot0) -> silence and
      no write -- the pinned HYP-PF-010 occupied fail-closure: the merge
      lane is unreachable without its dedicated opt-in profile

Scope guard: sockets + scratch DBs only.  Never launches, touches, or
automates GameClient.  Never opens the canonical state DB.  No repo writes
(--json and every --db file must point outside the repo).  stdlib only.

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


def move_pass(legacy, request_pc, args, db_path, checks, tag, *,
              expect_frame_sha, expect_rows, expect_write):
    """One full connection pass; True iff every expectation held."""
    ok = True
    s = enter_runtime_ready(
        legacy, args.host, args.game_port, db_path, args.window, checks, tag,
    )
    try:
        # Both before-reads happen after runtime-ready so a first-connection
        # character create never masquerades as a request effect.
        before_rows = backpack_rows(db_path)
        before_updated = backpack_updated_at(db_path)
        s.sendall(legacy.frame_pc(request_pc))
        stamped, eof = drain(s, args.window)
        others = non_heartbeats(stamped)
        checks[f"{tag}_dispatch_frames"] = [
            {"bytes": len(b), "sha256": _sha(b)} for _t, b in others
        ]
        checks[f"{tag}_eof"] = bool(eof)
        ok = ok and not eof
        if expect_frame_sha is None:
            checks[f"{tag}_silent_no_reply"] = not others
            ok = ok and not others
        else:
            exact = bool(
                len(others) == 1 and _sha(others[0][1]) == expect_frame_sha
            )
            checks[f"{tag}_response_byte_exact"] = exact
            ok = ok and exact
        after_rows = backpack_rows(db_path)
        after_updated = backpack_updated_at(db_path)
        checks[f"{tag}_rows_after"] = after_rows
        if expect_rows is not None:
            rows_ok = after_rows == expect_rows
            checks[f"{tag}_rows_expected"] = rows_ok
            ok = ok and rows_ok
        if expect_write:
            bumped = (
                before_updated is not None and after_updated is not None
                and after_updated > before_updated
            )
            checks[f"{tag}_updated_at_advanced"] = bumped
            ok = ok and bumped
        else:
            unchanged = (
                after_rows == before_rows and after_updated == before_updated
            )
            checks[f"{tag}_no_write"] = unchanged
            ok = ok and unchanged
        checks[f"{tag}_ok"] = ok
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
                    help="scratch DB for the exact-direction merge server, "
                         "OUTSIDE the repo; must exist (migrated)")
    ap.add_argument("--db-file-second", required=True,
                    help="second scratch DB for the generalized-slot merge "
                         "server, OUTSIDE the repo; must exist (migrated)")
    ap.add_argument("--db-file-pinned", required=True,
                    help="third scratch DB for the original-profile server, "
                         "OUTSIDE the repo; must exist (migrated)")
    ap.add_argument("--json", required=True)
    ap.add_argument("--window", type=float, default=2.0)
    ap.add_argument("--boot-wait", type=float, default=15.0)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    db_merge = Path(args.db_file).resolve()
    db_second = Path(args.db_file_second).resolve()
    db_pinned = Path(args.db_file_pinned).resolve()
    for required in (db_merge, db_second, db_pinned):
        if not required.is_file():
            print(f"scratch DB missing: {required}", file=sys.stderr)
            return 2
    for target in (db_merge, db_second, db_pinned, Path(args.json).resolve()):
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
        MERGED_V111_BACKPACK,
        make_item_merge_delta_response,
        make_item_move_delta_response,
        merge_known_item_into_occupied_slot,
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

    # Expected frames, computed from the same pure transitions the server
    # commits, then compared byte-for-byte against real TCP bytes.  The
    # exact direction must reproduce the frozen V141 golden the real client
    # accepted at V111 runtime -- that identity is asserted here, before any
    # socket opens.
    after_a, merged_a, consumed_a = merge_known_item_into_occupied_slot(
        INITIAL_BACKPACK, 3, 0,
    )
    _pc_a, frame_a = make_item_merge_delta_response(
        legacy, merged_a, consumed_a.identity,
    )
    _golden_pc, golden_frame = legacy.make_item_operate_stack_merge_success()
    assert frame_a == golden_frame
    assert after_a == MERGED_V111_BACKPACK
    after_b, moved_b = move_known_item_to_free_slot(INITIAL_BACKPACK, 1, 7)
    _pc_b, frame_b = make_item_move_delta_response(legacy, moved_b)
    _after_c, merged_c, consumed_c = merge_known_item_into_occupied_slot(
        after_b, 3, 7,
    )
    _pc_c, frame_c = make_item_merge_delta_response(
        legacy, merged_c, consumed_c.identity,
    )
    assert frame_c != golden_frame and len(frame_c) == len(golden_frame)

    verdict: dict = {"probe": "ITEM-MERGE-001", "checks": {}, "ok": False}
    checks = verdict["checks"]
    checks["response_pins"] = {
        "merge_id3_into_id1_slot0_frame_sha256": _sha(frame_a),
        "merge_frame_equals_frozen_v111_golden": frame_a == golden_frame,
        "free_move_id1_to_slot7_frame_sha256": _sha(frame_b),
        "merge_id3_into_id1_slot7_frame_sha256": _sha(frame_c),
        "merge_frame_size": len(frame_a),
        "free_frame_size": len(frame_b),
    }

    code = 3
    server = boot_server(
        root, db_merge,
        "scenarios/item_move_hypothesis_v111_occupied_merge.json",
        args.host, args.game_port, args.boot_wait,
    )
    if server is None:
        print("merge-profile server did not open the GAME port",
              file=sys.stderr)
        return 4
    try:
        ok_a = move_pass(
            legacy, request_pc(0, 3), args, db_merge, checks, "a",
            expect_frame_sha=_sha(frame_a),
            expect_rows=[(1, 0, 2, 2600001), (2, 1, 1, 2400901),
                         (4, 3, 1, 2200002)],
            expect_write=True,
        )
    except (OSError, socket.timeout) as exc:
        verdict["error"] = repr(exc)
        Path(args.json).write_text(json.dumps(verdict, indent=1),
                                   encoding="utf-8")
        print(json.dumps(verdict, indent=1))
        stop_server(server)
        return 4
    finally:
        stop_server(server)

    time.sleep(1.0)
    server = boot_server(
        root, db_second,
        "scenarios/item_move_hypothesis_v111_occupied_merge.json",
        args.host, args.game_port, args.boot_wait,
    )
    if server is None:
        print("second merge-profile server did not open the GAME port",
              file=sys.stderr)
        return 4
    try:
        ok_b = move_pass(
            legacy, request_pc(7, 1), args, db_second, checks, "b",
            expect_frame_sha=_sha(frame_b),
            expect_rows=[(1, 7, 1, 2600001), (2, 1, 1, 2400901),
                         (3, 2, 1, 2600001), (4, 3, 1, 2200002)],
            expect_write=True,
        )
        time.sleep(1.0)
        ok_c = move_pass(
            legacy, request_pc(7, 3), args, db_second, checks, "c",
            expect_frame_sha=_sha(frame_c),
            expect_rows=[(1, 7, 2, 2600001), (2, 1, 1, 2400901),
                         (4, 3, 1, 2200002)],
            expect_write=True,
        )
        time.sleep(1.0)
        ok_d = move_pass(
            legacy, request_pc(1, 4), args, db_second, checks, "d",
            expect_frame_sha=None, expect_rows=None, expect_write=False,
        )
        time.sleep(1.0)
        ok_e = move_pass(
            legacy, request_pc(1, 2), args, db_second, checks, "e",
            expect_frame_sha=None, expect_rows=None, expect_write=False,
        )
    except (OSError, socket.timeout) as exc:
        verdict["error"] = repr(exc)
        Path(args.json).write_text(json.dumps(verdict, indent=1),
                                   encoding="utf-8")
        print(json.dumps(verdict, indent=1))
        stop_server(server)
        return 4
    finally:
        stop_server(server)

    time.sleep(1.0)
    server = boot_server(
        root, db_pinned, "scenarios/item_move_hypothesis_v111_slot2.json",
        args.host, args.game_port, args.boot_wait,
    )
    if server is None:
        print("pinned-profile server did not open the GAME port",
              file=sys.stderr)
        return 4
    try:
        ok_f = move_pass(
            legacy, request_pc(0, 3), args, db_pinned, checks, "f",
            expect_frame_sha=None, expect_rows=None, expect_write=False,
        )
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
        checks.get(f"{tag}_heartbeats_before_request", 0) >= 1
        for tag in ("a", "b", "c", "d", "e", "f")
    )
    checks["heartbeat_seen_before_every_request"] = heartbeat_ok
    verdict["ok"] = bool(ok_a and ok_b and ok_c and ok_d and ok_e and ok_f
                         and heartbeat_ok)
    code = 0 if verdict["ok"] else 3
    Path(args.json).write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    print(json.dumps(verdict, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
