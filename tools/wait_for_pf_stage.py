#!/usr/bin/env python3
"""Wait for a decoded Pirate Force live-log milestone without blind sleeps."""
import argparse
from pathlib import Path
import sys
import time


STAGES = {
    "connected": ("GAME_CONNECTED",),
    "character-ready": ("NotifyEnterCreateActor",),
    "start-game": ("StartGameReq",),
    "teleport": ("SENT label=V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE",),
    "runtime-ready": ("SENT label=RUNTIME_RES_ACK_FIRST_REQ",),
    "population": (
        "SENT label=ARENA_V1_P30_INITIAL",
        "SENT label=V134_P0_P30_P91_ISOLATED_INITIAL_READY",
    ),
    "arena-target": ("arena_v1_p30_target_kind2_captured_no_reply",),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("stage", choices=sorted(STAGES))
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--poll-ms", type=float, default=100.0)
    args = parser.parse_args()
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        try:
            lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
        except FileNotFoundError:
            lines = []
        for line in reversed(lines):
            if any(needle in line for needle in STAGES[args.stage]):
                print(line)
                return 0
        time.sleep(max(args.poll_ms, 10.0) / 1000.0)
    print(f"timeout waiting for {args.stage!r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
