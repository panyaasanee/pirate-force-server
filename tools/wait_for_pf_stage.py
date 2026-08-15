#!/usr/bin/env python3
"""Wait for a decoded Pirate Force live-log milestone without blind sleeps."""
import argparse
from pathlib import Path
import sys
import time


STAGES = {
    "connected": (("GAME_CONNECTED",),),
    "character-list": (("SENT label=FOUNDATION_CHARACTER_LIST_ONCE",),),
    "character-ready": (("NotifyEnterCreateActor",),),
    "create-committed": (("SENT label=FOUNDATION_CREATE_COMMITTED",),),
    "start-game": (("StartGameReq",),),
    "teleport": (("SENT label=V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE",),),
    "scene2-start-game": (("SENT label=SCENE2_LOAD_ONLY_SELECTED_START_GAME",),),
    "scene2-teleport": (("SENT label=SCENE2_LOAD_ONLY_TELEPORT_MARKER2_ONCE",),),
    "scene2-fish-p60": (("SENT label=SCENE2_P60_MOBS34_SINGLE_INITIAL",),),
    "scene2-fish-p60-hp": (("SENT label=SCENE2_P60_MOBS34_HP3857_INITIAL",),),
    "runtime-ready": (("SENT label=RUNTIME_RES_ACK_FIRST_REQ",),),
    "population": (
        ("SENT label=ARENA_V2_P30_INITIAL",),
        ("SENT label=ARENA_V1_P30_INITIAL",),
        ("SENT label=V134_P0_P30_P91_ISOLATED_INITIAL_READY",),
    ),
    "arena-target": ((
        "name=TargetVital", "actor_id=0x000000000000201F",
        "placement=P30", "kind=2",
    ),),
}


def resolve_logs(path: Path) -> list[Path]:
    """Accept a live log, capture_vNN directory, or launcher capture root."""
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    candidates = [
        item for item in path.rglob("*.txt")
        if "GAME_LIVE" in item.name or "GAME_EVENTS_LIVE" in item.name
    ]
    return sorted(candidates, key=lambda item: (item.stat().st_mtime_ns, str(item)))


def find_stage_line(logs: list[Path], stage: str) -> str | None:
    matches: list[tuple[int, str]] = []
    for log in logs:
        try:
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        except FileNotFoundError:
            continue
        for line_no, line in enumerate(lines):
            if any(all(needle in line for needle in pattern) for pattern in STAGES[stage]):
                matches.append((log.stat().st_mtime_ns + line_no, line))
    return max(matches, default=(0, ""))[1] or None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path,
                        help="GAME live log, capture_vNN directory, or launcher capture root")
    parser.add_argument("stage", choices=sorted(STAGES))
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--poll-ms", type=float, default=100.0)
    args = parser.parse_args()
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        line = find_stage_line(resolve_logs(args.log), args.stage)
        if line is not None:
            print(line)
            return 0
        time.sleep(max(args.poll_ms, 10.0) / 1000.0)
    print(f"timeout waiting for {args.stage!r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
