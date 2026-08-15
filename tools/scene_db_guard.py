#!/usr/bin/env python3
"""Record and verify that a Scene load-only run never changes SQLite files."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import time


def snapshot(database: Path) -> dict:
    database = database.resolve(strict=True)
    result = {"schema": 1, "database": str(database), "files": {}}
    for suffix in ("", "-wal", "-shm"):
        path = Path(str(database) + suffix)
        exists = path.is_file()
        result["files"][suffix or "main"] = {
            "exists": exists,
            "bytes": path.stat().st_size if exists else None,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper() if exists else None,
        }
    return result


def compare(before: dict, after: dict) -> tuple[bool, list[str]]:
    if before.get("schema") != 1 or after.get("schema") != 1:
        raise ValueError("unsupported guard schema")
    if before.get("database") != after.get("database"):
        raise ValueError("database path changed")
    failures = []
    for key in ("main", "-wal", "-shm"):
        if before["files"].get(key) != after["files"].get(key):
            failures.append(key)
    return not failures, failures


def pid_alive(pid: int) -> bool:
    if not hasattr(ctypes, "windll"):
        return False
    query = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(query, False, pid)
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        return bool(ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("database", type=Path); snap.add_argument("output", type=Path)
    monitor = sub.add_parser("monitor")
    monitor.add_argument("before", type=Path); monitor.add_argument("output", type=Path)
    monitor.add_argument("--pid", type=int, action="append", required=True)
    args = parser.parse_args()
    if args.command == "snapshot":
        write_json(args.output, snapshot(args.database)); return 0
    before = json.loads(args.before.read_text(encoding="utf-8"))
    while any(pid_alive(pid) for pid in args.pid):
        time.sleep(0.5)
    after = snapshot(Path(before["database"]))
    passed, changed = compare(before, after)
    write_json(args.output, {
        "schema": 1, "verdict": "PASS_UNCHANGED" if passed else "FAIL_CHANGED",
        "changed": changed, "before": before, "after": after,
    })
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
