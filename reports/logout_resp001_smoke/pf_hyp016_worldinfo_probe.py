"""HYP-PF-016 headless probe: response-first logout, LOGOUT-RESP-001.

On a real server process running the worldinfo_first opt-in scenario over a
scratch DB, three serial passes over real TCP:

  pass A (subcode 01, capture_gt002 payload):
    login_verify -> create -> start_game -> first empty runtime req
    (runtime-ready) -> heartbeat observed -> full 248B GetWorldInfoVital
    (stored, NO reply) -> captured LogoutVital subcode 01 ->
      1. exactly two non-heartbeat frames, in order: the 283-byte 0x3D4B
         response byte-equal to the capture_gt002 pin, then the 46-byte ack
         byte-equal to the unchanged PF-012 subcode-01 pin
      2. sessions.closed_at of this lease committed BEFORE the first
         response byte arrived (same-host clocks)
      3. EOF strictly after the ack, inside the close window (~250 ms)
  pass B (negative): fresh connection, runtime-ready, NO GetWorldInfoVital
    sent -> LogoutVital subcode 03 -> silence: zero non-heartbeat frames,
    no EOF inside the window, lease closed_at stays NULL
  pass C (subcode 03, latest-stored): send capture_gt002 then
    capture_item_move_hyp001 -> response must be the hyp001 pin (the LAST
    stored payload), ack is the subcode-03 pin, same ordering/EOF/closed_at
    checks

Scope guard: sockets + a scratch DB only.  Never launches, touches, or
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
from datetime import datetime
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
    """Collect (recv_time, frame) until timeout or EOF; returns eof flag."""
    frames: list[tuple[float, bytes]] = []
    deadline = time.monotonic() + seconds
    while True:
        remain = deadline - time.monotonic()
        if remain <= 0:
            return frames, False, None
        sock.settimeout(remain)
        try:
            frame = recv_frame(sock)
        except socket.timeout:
            return frames, False, None
        except OSError:
            return frames, True, time.time()
        if frame is None:
            return frames, True, time.time()
        frames.append((time.time(), frame))


def non_heartbeats(stamped):
    return [(t, b) for t, b in stamped if _sha(b) != HEARTBEAT_FRAME_SHA256]


def latest_lease(db_path: Path):
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = db.execute(
            "SELECT id, opened_at, closed_at FROM sessions "
            "ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        return row
    finally:
        db.close()


def lease_closed_at(db_path: Path, sid: str):
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = db.execute(
            "SELECT closed_at FROM sessions WHERE id=?", (sid,),
        ).fetchone()
        return row[0] if row else None
    finally:
        db.close()


def iso_epoch(text: str) -> float:
    return datetime.fromisoformat(text).timestamp()


def enter_runtime_ready(legacy, host, port, db_path, window, checks, tag):
    """login -> (create) -> start_game -> empty runtime req; returns socket."""
    s = socket.create_connection((host, port), timeout=8.0)
    s.sendall(legacy.frame_pc(legacy._synthetic_client_login_pc()))
    frames, eof, _ = drain(s, window)
    checks[f"{tag}_login_reply_frames"] = len(non_heartbeats(frames))
    lease = latest_lease(db_path)
    checks[f"{tag}_lease_id"] = lease[0] if lease else None

    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        actives = db.execute(
            "SELECT selector FROM characters WHERE deleted_at IS NULL"
        ).fetchall()
    finally:
        db.close()
    if not actives:
        s.sendall(legacy.frame_pc(legacy._V25_REAL_CREATE_PC))
        frames, eof, _ = drain(s, window)
        checks[f"{tag}_create_reply_frames"] = len(non_heartbeats(frames))
        db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            actives = db.execute(
                "SELECT selector FROM characters WHERE deleted_at IS NULL"
            ).fetchall()
        finally:
            db.close()
    selector = int(actives[0][0])

    s.sendall(legacy.frame_pc(legacy._synthetic_start_game_pc(selector)))
    frames, eof, _ = drain(s, window)
    checks[f"{tag}_start_game_reply_frames"] = len(non_heartbeats(frames))

    s.sendall(legacy.frame_pc(legacy.V136_EMPTY_RUNTIME_REQ_PC))
    frames, eof, _ = drain(s, window)
    checks[f"{tag}_runtime_ready_reply_frames"] = len(non_heartbeats(frames))

    # The frozen v141 clock heartbeat must be flowing before the logout.
    frames, eof, _ = drain(s, 2.6)
    checks[f"{tag}_heartbeats_before_logout"] = len(frames) - len(
        non_heartbeats(frames)
    )
    return s


def logout_pass(legacy, mod, args, checks, verdict_key, *, tag, subcode,
                worldinfo_payloads, expect_response_probe):
    """One full connection pass; populates checks[<tag>_*]."""
    ok = True
    s = enter_runtime_ready(
        legacy, args.host, args.game_port, Path(args.db_file),
        args.window, checks, tag,
    )
    try:
        worldinfo_pc_prefix = (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, mod.WORLDINFO_FULL_VITAL_COUNT)
            + legacy.u16tag(0x12, mod.WORLDINFO_VITAL_ID)
            + legacy.u8tag(0x0B, 0)
        )
        for probe_name in worldinfo_payloads:
            payload = mod.WORLDINFO_PROBE_PAYLOADS[probe_name]
            s.sendall(legacy.frame_pc(worldinfo_pc_prefix + payload))
            frames, eof, _ = drain(s, args.window)
            checks[f"{tag}_worldinfo_{probe_name}_reply_frames"] = len(
                non_heartbeats(frames)
            )
            ok = ok and not non_heartbeats(frames) and not eof

        lease_id = checks[f"{tag}_lease_id"]
        t_logout_sent = time.time()
        s.sendall(legacy.frame_pc(mod.LOGOUT_REQUEST_PCS[subcode]))
        stamped, eof, eof_at = drain(s, args.close_window)
        others = non_heartbeats(stamped)
        checks[f"{tag}_dispatch_frames"] = [
            {"bytes": len(b), "sha256": _sha(b)} for _t, b in others
        ]
        checks[f"{tag}_heartbeat_frames_in_window"] = (
            len(stamped) - len(others)
        )
        checks[f"{tag}_eof"] = bool(eof)

        if expect_response_probe is None:
            # Negative: silence, no EOF, no write.
            checks[f"{tag}_silent_no_reply"] = not others
            closed = lease_closed_at(Path(args.db_file), lease_id)
            checks[f"{tag}_closed_at_stays_null"] = closed is None
            checks[f"{tag}_no_eof_in_window"] = not eof
            ok = ok and not others and closed is None and not eof
        else:
            response_pin = mod.WORLDINFO_PROBE_RESPONSE_FRAME_SHA256[
                expect_response_probe
            ]
            ack_pin = mod.LOGOUT_ACK_FRAME_SHA256[subcode]
            ordered = bool(
                len(others) == 2
                and len(others[0][1]) == mod.WORLDINFO_RESPONSE_FRAME_SIZE
                and _sha(others[0][1]) == response_pin
                and len(others[1][1]) == 46
                and _sha(others[1][1]) == ack_pin
            )
            checks[f"{tag}_response_then_ack_byte_exact"] = ordered
            ok = ok and ordered

            closed = lease_closed_at(Path(args.db_file), lease_id)
            checks[f"{tag}_closed_at"] = closed
            committed_before_response = False
            if closed is not None and ordered:
                closed_epoch = iso_epoch(closed)
                t_response = others[0][0]
                checks[f"{tag}_closed_at_minus_logout_send_ms"] = round(
                    (closed_epoch - t_logout_sent) * 1000.0, 1,
                )
                checks[f"{tag}_response_minus_closed_at_ms"] = round(
                    (t_response - closed_epoch) * 1000.0, 1,
                )
                committed_before_response = closed_epoch <= t_response
            checks[f"{tag}_closed_at_before_response"] = (
                committed_before_response
            )
            ok = ok and committed_before_response

            fin_after_ack = False
            if eof and ordered and eof_at is not None:
                t_ack = others[1][0]
                delta_ms = (eof_at - t_ack) * 1000.0
                checks[f"{tag}_eof_after_ack_ms"] = round(delta_ms, 1)
                fin_after_ack = (
                    args.min_close_ms <= delta_ms <= args.max_close_ms
                )
            checks[f"{tag}_fin_after_ack_in_window"] = fin_after_ack
            ok = ok and fin_after_ack
        checks[verdict_key] = ok
        return ok
    finally:
        try:
            s.close()
        except OSError:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True,
                    help="Pirate Force ServerProject checkout root")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--game-port", type=int, default=10189)
    ap.add_argument("--db-file", required=True,
                    help="scratch DB path OUTSIDE the repo; must exist "
                         "(migrated) before the server boots")
    ap.add_argument("--json", required=True,
                    help="verdict JSON path OUTSIDE the repo")
    ap.add_argument("--window", type=float, default=2.0)
    ap.add_argument("--close-window", type=float, default=6.0)
    ap.add_argument("--min-close-ms", type=float, default=100.0)
    ap.add_argument("--max-close-ms", type=float, default=2000.0)
    ap.add_argument("--boot-wait", type=float, default=15.0)
    ap.add_argument("--no-server", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    db_path = Path(args.db_file).resolve()
    if not db_path.is_file():
        print(f"scratch DB missing: {db_path}", file=sys.stderr)
        return 2
    for target in (db_path, Path(args.json).resolve()):
        try:
            target.relative_to(root)
        except ValueError:
            continue
        print(f"refusing repo write target: {target}", file=sys.stderr)
        return 2

    legacy = _load_legacy(root)
    sys.path.insert(0, str(root / "src"))
    import pirateforce_foundation.logout_hypothesis as mod  # noqa: E402

    verdict: dict = {"probe": "LOGOUT-RESP-001", "checks": {}, "ok": False}
    checks = verdict["checks"]
    checks["request_pins"] = {
        "logout_subcode01_pc_sha256": _sha(mod.LOGOUT_REQUEST_PCS[1]),
        "logout_subcode03_pc_sha256": _sha(mod.LOGOUT_REQUEST_PCS[3]),
        "worldinfo_gt002_payload_sha256": mod.WORLDINFO_PROBE_PAYLOAD_SHA256[
            "capture_gt002"
        ],
        "worldinfo_hyp001_payload_sha256": mod.WORLDINFO_PROBE_PAYLOAD_SHA256[
            "capture_item_move_hyp001"
        ],
    }

    server = None
    if not args.no_server:
        server = subprocess.Popen(
            [sys.executable, "-m", "pirateforce_foundation.app",
             "--db", str(db_path),
             "--logout-hypothesis-scenario",
             str(root / "scenarios/logout_hypothesis_worldinfo_first.json")],
            cwd=root, env={**__import__("os").environ,
                           "PYTHONPATH": str(root / "src")},
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + args.boot_wait
        while time.monotonic() < deadline:
            try:
                socket.create_connection(
                    (args.host, args.game_port), timeout=0.5,
                ).close()
                break
            except OSError:
                time.sleep(0.4)
        else:
            print("server did not open the GAME port", file=sys.stderr)
            if server:
                server.terminate()
            return 4

    code = 3
    try:
        ok_a = logout_pass(
            legacy, mod, args, checks, "pass_a_ok",
            tag="a", subcode=1,
            worldinfo_payloads=("capture_gt002",),
            expect_response_probe="capture_gt002",
        )
        time.sleep(1.0)
        ok_b = logout_pass(
            legacy, mod, args, checks, "pass_b_ok",
            tag="b", subcode=3,
            worldinfo_payloads=(),
            expect_response_probe=None,
        )
        time.sleep(1.0)
        ok_c = logout_pass(
            legacy, mod, args, checks, "pass_c_ok",
            tag="c", subcode=3,
            worldinfo_payloads=("capture_gt002", "capture_item_move_hyp001"),
            expect_response_probe="capture_item_move_hyp001",
        )
        heartbeat_ok = all(
            checks.get(f"{tag}_heartbeats_before_logout", 0) >= 1
            for tag in ("a", "b", "c")
        )
        checks["heartbeat_seen_before_every_logout"] = heartbeat_ok
        no_reply_on_store = all(
            value == 0 for key, value in checks.items()
            if "_worldinfo_" in key and key.endswith("_reply_frames")
        )
        checks["worldinfo_frames_never_answered"] = no_reply_on_store
        verdict["ok"] = bool(
            ok_a and ok_b and ok_c and heartbeat_ok and no_reply_on_store
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
        Path(args.json).write_text(
            json.dumps(verdict, indent=1), encoding="utf-8",
        )
        print(json.dumps(verdict, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
