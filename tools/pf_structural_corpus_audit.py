#!/usr/bin/env python3
"""Deterministic audit of anchored decoded structural protocol lines only."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path(__file__).with_name("pf_structural_corpus_audit_config.json")
DEFAULT_OUTPUT_ROOT = ROOT / "reports" / "capture_corpus_audit"
DIRECTIONS = {"client_to_server", "server_to_client"}
PROVENANCE = {"game_client_to_local_emulator", "original_server_capture"}
EXACT_CONFIG_SHA256 = "E21034E56B5B060A157F36BAB597685230315C4B1633A9793B0333193B22CD42"
STRUCTURAL = re.compile(r"^STRUCTURAL_IDS (\[.*\]) OUTER version=(\d+) mask=0x([0-9A-Fa-f]+) count=(\d+) nested_version=(None|\d+)$")
RECV = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}) RECV frame=(\d+) pc_len=(\d+) ids=(\[.*\])$")


@dataclass(frozen=True)
class DecodedFrame:
    ids: tuple[tuple[int, int, str], ...]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _ids(raw: str) -> tuple[tuple[int, int, str], ...]:
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError) as exc:
        raise ValueError("malformed anchored ids list") from exc
    if type(value) is not list or not value:
        raise ValueError("anchored ids list must be nonempty")
    out = []
    for item in value:
        if type(item) is not tuple or len(item) != 3 or type(item[0]) is not int or type(item[1]) is not int or type(item[2]) is not str:
            raise ValueError("invalid anchored id tuple")
        if item[0] < 0 or not 0 <= item[1] <= 0xFFFF or not item[2]:
            raise ValueError("anchored id tuple out of bounds")
        out.append(item)
    if out[0][0] != 0 or any(out[i][0] <= out[i - 1][0] for i in range(1, len(out))):
        raise ValueError("anchored id offsets are not strictly ordered from zero")
    return tuple(out)


def parse_lines(lines: Iterable[str]) -> list[DecodedFrame]:
    frames: list[DecodedFrame] = []
    for raw in lines:
        line = raw.rstrip("\r\n")
        if line.startswith("STRUCTURAL_IDS "):
            match = STRUCTURAL.fullmatch(line)
            if not match:
                raise ValueError("malformed STRUCTURAL_IDS anchor")
            ids = _ids(match.group(1))
            count = int(match.group(4))
            nested = None if match.group(5) == "None" else int(match.group(5))
            if count not in {0, 1, 2, 3} or len(ids) - 1 > count:
                raise ValueError("structural anchor count is outside the exact corpus grammar")
            if count == 0 and (len(ids) != 1 or nested is not None):
                raise ValueError("empty structural anchor is inconsistent")
            if count > 0 and (len(ids) < 2 or nested is None):
                raise ValueError("nested structural anchor is inconsistent")
            frames.append(DecodedFrame(ids))
        elif re.match(r"^\d{4}-\d\d-\d\dT.* RECV ", line):
            match = RECV.fullmatch(line)
            if not match:
                raise ValueError("malformed timestamped RECV anchor")
            frames.append(DecodedFrame(_ids(match.group(4))))
    return frames


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if sha256(canonical) != EXACT_CONFIG_SHA256:
        raise ValueError("corpus manifest differs from exact allowlist")
    if type(data) is not dict or set(data) != {"schema", "sources", "targets"} or data["schema"] != 1:
        raise ValueError("invalid corpus config root")
    if type(data["sources"]) is not list or not data["sources"] or type(data["targets"]) is not dict:
        raise ValueError("invalid corpus config collections")
    logical: set[str] = set(); locations: set[tuple[str, str | None]] = set(); payloads: set[tuple[int, str]] = set()
    for source in data["sources"]:
        common = {"logical_id", "path", "container", "size", "sha256", "direction", "provenance"}
        expected = common | ({"member", "member_size", "member_sha256"} if source.get("container") == "zip" else set())
        if type(source) is not dict or set(source) != expected or source["container"] not in {"plain", "zip"}:
            raise ValueError("invalid corpus source schema")
        if source["logical_id"] in logical or (source["path"], source.get("member")) in locations:
            raise ValueError("duplicate logical capture source")
        logical.add(source["logical_id"]); locations.add((source["path"], source.get("member")))
        if source["direction"] not in DIRECTIONS or source["provenance"] not in PROVENANCE:
            raise ValueError("unknown direction or provenance")
        size_key = source.get("member_size", source["size"]); hash_key = source.get("member_sha256", source["sha256"])
        if (size_key, hash_key) in payloads:
            raise ValueError("duplicate logical payload")
        payloads.add((size_key, hash_key))
    for key, name in data["targets"].items():
        if not key.isdecimal() or not 0 <= int(key) <= 0xFFFF or type(name) is not str or not name:
            raise ValueError("invalid target registry")
    return data


def source_text(source: dict[str, Any]) -> str:
    path = (ROOT / source["path"]).resolve()
    if ROOT not in path.parents or path.stat().st_size != source["size"] or sha256(path.read_bytes()) != source["sha256"]:
        raise ValueError(f"evidence guard mismatch: {source['logical_id']}")
    if source["container"] == "plain":
        data = path.read_bytes()
    else:
        with zipfile.ZipFile(path) as archive:
            if archive.namelist() != [source["member"]]:
                raise ValueError("zip member manifest mismatch")
            data = archive.read(source["member"])
        if len(data) != source["member_size"] or sha256(data) != source["member_sha256"]:
            raise ValueError("zip member evidence guard mismatch")
    return data.decode("utf-8", errors="strict")


def audit(config: dict[str, Any]) -> dict[str, Any]:
    targets = {int(k): v for k, v in config["targets"].items()}
    total_outer: Counter[int] = Counter(); total_nested: Counter[int] = Counter(); target_counts: Counter[int] = Counter(); eligible_target_counts: Counter[int] = Counter()
    eligible = 0; results = []
    for source in sorted(config["sources"], key=lambda value: value["logical_id"]):
        frames = parse_lines(source_text(source).splitlines())
        outer: Counter[int] = Counter(); nested: Counter[int] = Counter()
        for frame in frames:
            outer[frame.ids[0][1]] += 1
            for item in frame.ids[1:]: nested[item[1]] += 1
        is_eligible = source["direction"] == "server_to_client" and source["provenance"] == "original_server_capture"
        if is_eligible: eligible += len(frames)
        total_outer.update(outer); total_nested.update(nested)
        for key in targets: target_counts[key] += outer[key] + nested[key]
        if is_eligible:
            for key in targets: eligible_target_counts[key] += outer[key] + nested[key]
        results.append({"logical_id": source["logical_id"], "direction": source["direction"], "provenance": source["provenance"], "decoded_frames": len(frames), "outer_ids": {str(k): outer[k] for k in sorted(outer)}, "nested_ids": {str(k): nested[k] for k in sorted(nested)}, "eligible_original_server_to_client": is_eligible})
    return {"schema": 1, "claim": "bounded_structural_corpus_capability", "sources": results, "totals": {"decoded_frames": sum(item["decoded_frames"] for item in results), "outer_ids": {str(k): total_outer[k] for k in sorted(total_outer)}, "nested_ids": {str(k): total_nested[k] for k in sorted(total_nested)}}, "combat_targets": {str(k): {"name": targets[k], "all_directions_count": target_counts[k], "eligible_original_server_to_client_count": eligible_target_counts[k]} for k in sorted(targets)}, "eligible_original_server_to_client_frames": eligible, "no_eligible_original_server_to_client_frames": eligible == 0, "bounded_target_negative": eligible > 0 and all(value == 0 for value in eligible_target_counts.values()), "nonclaim": "zero counts describe only the guarded decoded corpus; they do not prove protocol absence"}


def output_path(path: Path) -> Path:
    resolved = path.resolve()
    root = DEFAULT_OUTPUT_ROOT.resolve()
    if root != resolved.parent or resolved.suffix.lower() != ".json":
        raise ValueError("output must be a JSON file directly under the dedicated audit root")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = audit(load_config(args.config.resolve()))
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    if args.output:
        destination = output_path(args.output); destination.parent.mkdir(parents=True, exist_ok=True); destination.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
