"""HYP-PF-014 headless probe: speaker-name wstring echo variant, CHAT-ECHO-002.

On a real server process running the speaker echo opt-in scenario
(scenarios/chat_input_hypothesis_speaker_echo.json) over a fresh migrated
scratch DB, drive the full wire entry on one connection --
login_verify -> character list -> create (real captured V25 create PC, whose
persisted canonical name is the pinned probe speaker name) -> start_game ->
exact empty runtime req (runtime-ready ack) -- then send the two byte-exact
captured GT-006 chat input request PCs as probe1, probe2, probe1-again and
verify, per send:

  1. exactly one non-heartbeat frame arrives in the window -- 79 bytes,
     sha256 equal to the pinned speaker echo frame (the module pins and a
     locally composed make_chat_input_speaker_echo_response must agree)
  2. no other dispatch frame arrives and the server does NOT close the
     socket (the lane is no-close by design)
  3. the third send (probe1 repeated) is echoed again: not one-shot

and, for the whole run:

  4. a SHORT off-shape payload (the GT-009-observed 20-byte 5-character
     form) stays silent: no reply, no EOF
  5. the server database file bytes are unchanged across the whole chat
     window including the SHORT negative (sha256 before == after) -- the
     lane writes nothing
  6. the frozen v141 clock heartbeat keeps its cadence in the tail drain
     (>= min-tail-heartbeats heartbeats, zero dispatch frames).

Scope guard: sockets + a scratch DB only.  Never launches, touches, or
automates GameClient.  Never opens the canonical state DB.  No repo writes
(--json must point outside the repo).  stdlib + repo imports only.

Exit codes
  0  all criteria held
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


def _say(text: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)


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


def drain(sock: socket.socket, seconds: float) -> tuple[list[bytes], bool]:
    frames: list[bytes] = []
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
        if frame is None:
            return frames, True
        frames.append(frame)


def non_heartbeats(frames: list[bytes]) -> list[bytes]:
    return [b for b in frames if _sha(b) != HEARTBEAT_FRAME_SHA256]


def db_characters(db_path: Path) -> list[tuple]:
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return db.execute(
            "SELECT selector,name,deleted_at FROM characters ORDER BY id"
        ).fetchall()
    finally:
        db.close()


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
    ap.add_argument("--window", type=float, default=3.0)
    ap.add_argument("--boot-wait", type=float, default=30.0)
    ap.add_argument("--tail", type=float, default=4.5)
    ap.add_argument("--min-tail-heartbeats", type=int, default=2)
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
    from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
        CHAT_INPUT_PROBE_PAYLOADS,
        CHAT_INPUT_PROBE_REQUEST_PCS,
        CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256,
        CHAT_INPUT_SPEAKER_ECHO_FRAME_SIZE,
        CHAT_INPUT_SPEAKER_PROBE_NAME,
        CHAT_INPUT_VITAL_ID,
        make_chat_input_speaker_echo_response,
    )

    # Cross-check: the locally composed expected reply must agree with the
    # module pins before any byte hits the wire.
    expected_frame_sha: dict[str, str] = {}
    for probe in ("probe1", "probe2"):
        _pc, frame = make_chat_input_speaker_echo_response(
            legacy, CHAT_INPUT_PROBE_PAYLOADS[probe],
            CHAT_INPUT_SPEAKER_PROBE_NAME,
        )
        expected_frame_sha[probe] = _sha(frame)
        if expected_frame_sha[probe] != (
            CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256[probe]
        ):
            print(f"pin drift for {probe}", file=sys.stderr)
            return 2
        _say(f"expected {probe}: {len(frame)}B "
             f"sha {expected_frame_sha[probe][:8]}..{expected_frame_sha[probe][-4:]}")

    # SHORT negative request (the GT-009-observed 5-character off-shape):
    # same one-vital request envelope, 20-byte payload -> wrong_length.
    short_payload = (
        b"\x48" + (0).to_bytes(4, "little")
        + b"\x48" + (10).to_bytes(4, "little")
        + "SHORT".encode("utf-16-le")
    )
    short_pc = bytes(
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, CHAT_INPUT_VITAL_ID)
        + legacy.u8tag(0x0B, 0)
        + short_payload
    )

    verdict: dict = {"probe": "CHAT-ECHO-002", "checks": {}, "ok": False}
    checks = verdict["checks"]

    server = subprocess.Popen(
        [sys.executable, "-m", "pirateforce_foundation.app",
         "--db", str(db_path),
         "--chat-input-hypothesis-scenario",
         str(root / "scenarios/chat_input_hypothesis_speaker_echo.json")],
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
        server.terminate()
        return 4
    _say("server GAME port open")

    code = 3
    sends: list[dict] = []
    try:
        sock = socket.create_connection((args.host, args.game_port),
                                        timeout=8.0)
        # ---- wire entry: login -> create -> select -> runtime-ready -------
        sock.sendall(legacy.frame_pc(legacy._synthetic_client_login_pc()))
        frames, eof = drain(sock, args.window)
        checks["login_reply_frames"] = len(non_heartbeats(frames))
        _say(f"login: {checks['login_reply_frames']} reply frames, eof {eof}")

        sock.sendall(legacy.frame_pc(legacy._V25_REAL_CREATE_PC))
        frames, eof = drain(sock, args.window)
        checks["create_reply_frames"] = len(non_heartbeats(frames))
        rows = [r for r in db_characters(db_path) if r[2] is None]
        checks["created_characters"] = len(rows)
        checks["persisted_name_is_probe_name"] = bool(
            len(rows) == 1 and rows[0][1] == CHAT_INPUT_SPEAKER_PROBE_NAME
        )
        _say(f"create: {checks['create_reply_frames']} reply frames, "
             f"characters {rows!r}")
        if not rows:
            raise AssertionError("create committed no character row")
        selector = rows[0][0]

        sock.sendall(legacy.frame_pc(
            legacy._synthetic_start_game_pc(selector)
        ))
        frames, eof = drain(sock, args.window)
        checks["start_game_reply_frames"] = len(non_heartbeats(frames))
        _say(f"start_game selector {selector}: "
             f"{checks['start_game_reply_frames']} reply frames, eof {eof}")

        sock.sendall(legacy.frame_pc(legacy.V136_EMPTY_RUNTIME_REQ_PC))
        frames, eof = drain(sock, args.window)
        checks["runtime_ready_reply_frames"] = len(non_heartbeats(frames))
        _say(f"runtime-ready: {checks['runtime_ready_reply_frames']} "
             f"reply frames, eof {eof}")

        # ---- speaker echo window ------------------------------------------
        db_before = _sha(db_path.read_bytes())
        verdict["db_sha256_before_chat"] = db_before
        for number, probe in enumerate(("probe1", "probe2", "probe1"), 1):
            result: dict = {"send": number, "probe": probe}
            sent_at = time.monotonic()
            sock.sendall(legacy.frame_pc(CHAT_INPUT_PROBE_REQUEST_PCS[probe]))
            frames = []
            first_dispatch_at = None
            eof = False
            window_deadline = time.monotonic() + args.window
            while time.monotonic() < window_deadline and not eof:
                got, eof = drain(sock, 0.05)
                for blob in got:
                    frames.append(blob)
                    if first_dispatch_at is None and (
                        _sha(blob) != HEARTBEAT_FRAME_SHA256
                    ):
                        first_dispatch_at = time.monotonic()
            others = non_heartbeats(frames)
            result["window_frames"] = len(frames)
            result["window_heartbeats"] = len(frames) - len(others)
            result["dispatch_sizes"] = [len(b) for b in others]
            result["dispatch_sha256"] = [_sha(b) for b in others]
            result["echo_byte_exact"] = bool(
                len(others) == 1
                and len(others[0]) == CHAT_INPUT_SPEAKER_ECHO_FRAME_SIZE
                and result["dispatch_sha256"][0] == expected_frame_sha[probe]
            )
            if result["echo_byte_exact"] and first_dispatch_at is not None:
                result["echo_after_send_ms"] = round(
                    (first_dispatch_at - sent_at) * 1000.0, 1,
                )
            result["eof"] = eof
            sends.append(result)
            _say(f"send {number} ({probe}): echo_byte_exact = "
                 f"{result['echo_byte_exact']} (non-heartbeat "
                 f"{result['dispatch_sizes']}, heartbeats "
                 f"{result['window_heartbeats']}, eof {eof})")

        # ---- SHORT negative -----------------------------------------------
        sock.sendall(legacy.frame_pc(short_pc))
        frames, eof = drain(sock, args.window)
        short_others = non_heartbeats(frames)
        checks["short_reply_frames"] = len(short_others)
        checks["short_silent_no_eof"] = bool(not short_others and not eof)
        _say(f"SHORT: {checks['short_reply_frames']} reply frames, eof {eof}")

        db_after = _sha(db_path.read_bytes())
        verdict["db_sha256_after_chat"] = db_after
        checks["db_unchanged_across_chat"] = bool(db_before == db_after)

        # ---- heartbeat tail -----------------------------------------------
        frames, eof = drain(sock, args.tail)
        tail_others = non_heartbeats(frames)
        checks["tail_heartbeats"] = len(frames) - len(tail_others)
        checks["tail_dispatch_frames"] = len(tail_others)
        checks["heartbeat_continues"] = bool(
            checks["tail_heartbeats"] >= args.min_tail_heartbeats
            and not tail_others
        )
        checks["eof"] = eof
        _say(f"tail: heartbeats {checks['tail_heartbeats']}, dispatch "
             f"{checks['tail_dispatch_frames']}, eof {eof}")
        sock.close()

        verdict["sends"] = sends
        verdict["ok"] = bool(
            checks["persisted_name_is_probe_name"]
            and len(sends) == 3
            and all(s["echo_byte_exact"] and not s["eof"] for s in sends)
            and checks["short_silent_no_eof"]
            and checks["db_unchanged_across_chat"]
            and checks["heartbeat_continues"]
        )
        code = 0 if verdict["ok"] else 3
    except (OSError, socket.timeout) as exc:
        verdict["error"] = repr(exc)
        code = 4
    except AssertionError as exc:
        verdict["error"] = repr(exc)
        code = 3
    finally:
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
