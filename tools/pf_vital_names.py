#!/usr/bin/env python3
"""Loader for docs/PF_VITAL_NAMES.json - the project's single source of truth
for Vital wire id -> class name.

Pure stdlib. No side effects on import.

Why this module exists
----------------------
Before NAMES-HOME-001 the only id->name table in the project lived inside
``current/pf_login_game_server_v141.py``.  That file is a FROZEN DELIVERY
SNAPSHOT (the previous AI's from-scratch server, kept byte-identical so the
rewrite can be diffed against it) and must never be edited, so anyone who
resolved a new wire id had nowhere to record it.  ``docs/PF_VITAL_NAMES.json``
is that home; this module is how code reads it.

Add new names to docs/PF_VITAL_NAMES.json ONLY.  Never to v141.
See the ``__doc__`` array at the top of the JSON for the admission rules.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TABLE = ROOT / "docs" / "PF_VITAL_NAMES.json"
DEFAULT_V141 = ROOT / "current" / "pf_login_game_server_v141.py"


class VitalNamesError(Exception):
    """Raised when the names table (or the v141 cross-check) is malformed."""


# --------------------------------------------------------------------------
# round-62 wire id algorithm (PF-NAMEID-HASH-001, commit 7c66b21)
#   uint16 id = ( sum_i (signed char)name[i] * (i + 1) ) mod 2^16
# Byte-identical to the disassembled client routine:
#   movsx di, byte ; imul di, bx (1-based index) ; add dx, di ; mov ax, dx ; ret 4
# --------------------------------------------------------------------------
def wire_id(name: str) -> int:
    """Return the 16-bit Vital wire id for a class name."""
    total = 0
    for index, byte in enumerate(name.encode("latin1")):
        signed = byte - 256 if byte >= 128 else byte
        total += signed * (index + 1)
    return total & 0xFFFF


class VitalNamesTable:
    """Parsed view of docs/PF_VITAL_NAMES.json."""

    def __init__(self, raw: dict, path: Path):
        self.raw = raw
        self.path = path
        self.doc = raw.get("__doc__", [])
        self.entries = raw.get("entries", [])
        self.by_id = {}
        self.by_name = {}
        for entry in self.entries:
            ident = entry["id_dec"]
            name = entry["name"]
            if ident in self.by_id:
                raise VitalNamesError(
                    f"{path}: duplicate id 0x{ident:04X} ({name})"
                )
            if name in self.by_name:
                raise VitalNamesError(f"{path}: duplicate name {name}")
            self.by_id[ident] = entry
            self.by_name[name] = entry

    def __len__(self) -> int:
        return len(self.entries)

    def name_for(self, ident: int, default=None):
        entry = self.by_id.get(ident)
        return entry["name"] if entry else default

    def names(self) -> dict:
        """id -> name mapping, drop-in replacement for the v141 NAMES dict."""
        return {ident: entry["name"] for ident, entry in self.by_id.items()}

    def hash_mismatches(self) -> list:
        """Entries whose name does not hash to their declared id."""
        bad = []
        for entry in self.entries:
            got = wire_id(entry["name"])
            if got != entry["id_dec"]:
                bad.append((entry["name"], entry["id_dec"], got))
        return bad


def load_names_table(path=None) -> VitalNamesTable:
    """Load and structurally validate docs/PF_VITAL_NAMES.json."""
    path = Path(path) if path is not None else DEFAULT_TABLE
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VitalNamesError(f"names table missing: {path}") from exc
    except ValueError as exc:
        raise VitalNamesError(f"names table is not valid JSON: {path}: {exc}") from exc

    if not isinstance(raw.get("entries"), list) or not raw["entries"]:
        raise VitalNamesError(f"{path}: 'entries' must be a non-empty list")

    required = ("id", "id_dec", "name", "source", "evidence")
    for position, entry in enumerate(raw["entries"]):
        if not isinstance(entry, dict):
            raise VitalNamesError(f"{path}: entry #{position} is not an object")
        missing = [key for key in required if key not in entry]
        if missing:
            raise VitalNamesError(
                f"{path}: entry #{position} ({entry.get('name', '?')}) "
                f"is missing field(s): {', '.join(missing)}"
            )
        if entry["id"].upper() != f"0X{entry['id_dec']:04X}":
            raise VitalNamesError(
                f"{path}: entry {entry['name']} has id {entry['id']} but "
                f"id_dec {entry['id_dec']} (0x{entry['id_dec']:04X}); the two must agree"
            )
        if not entry["evidence"]:
            raise VitalNamesError(
                f"{path}: entry {entry['name']} has an empty 'evidence' list; "
                "every name needs a pointer to where it came from"
            )

    declared = raw.get("entry_count")
    if declared is not None and declared != len(raw["entries"]):
        raise VitalNamesError(
            f"{path}: entry_count says {declared} but there are "
            f"{len(raw['entries'])} entries; update entry_count"
        )
    return VitalNamesTable(raw, path)


# --------------------------------------------------------------------------
# v141 frozen-snapshot cross-check (read-only; NEVER write to that file)
# --------------------------------------------------------------------------
_CONST_RE = re.compile(r"^([A-Z][A-Z0-9_]+)\s*=\s*(0x[0-9A-Fa-f]+)\s*$", re.M)
_ENTRY_RE = re.compile(r'(0x[0-9A-Fa-f]+|[A-Z][A-Z0-9_]+)\s*:\s*"([^"]+)"')


def parse_v141_names(path=None) -> list:
    """Parse the NAMES dict out of the frozen v141 snapshot BY READING ONLY.

    Returns a list of (id_int, name, const_name_or_None).
    Same parse the PF-NAMEID-RESOLVE-001 verifier has always used.
    """
    path = Path(path) if path is not None else DEFAULT_V141
    if not path.exists():
        raise VitalNamesError(f"v141 snapshot missing: {path}")
    src = path.read_text(encoding="utf-8")
    consts = {m.group(1): int(m.group(2), 16) for m in _CONST_RE.finditer(src)}
    block = re.search(r"NAMES\s*=\s*\{(.*?)\n\}", src, re.S)
    if not block:
        raise VitalNamesError(f"{path}: NAMES table not found")
    pairs = []
    for match in _ENTRY_RE.finditer(block.group(1)):
        key, name = match.group(1), match.group(2)
        value = int(key, 16) if key.startswith("0x") else consts.get(key)
        if value is None:
            continue
        pairs.append((value, name, None if key.startswith("0x") else key))
    return pairs


def cross_check_v141(table: VitalNamesTable, pairs=None) -> list:
    """Return human-readable problems if the table does not cover v141 NAMES.

    Empty list == the table is a superset of v141 NAMES and every overlapping
    id carries the identical name.
    """
    if pairs is None:
        pairs = parse_v141_names()
    problems = []
    for ident, name, const in pairs:
        entry = table.by_id.get(ident)
        label = const or f"0x{ident:04X}"
        if entry is None:
            problems.append(
                f"0x{ident:04X} ({name}, v141 NAMES[{label}]) is missing from "
                f"{table.path.name}. FIX: add it to docs/PF_VITAL_NAMES.json - "
                f"do NOT edit the frozen v141 snapshot."
            )
        elif entry["name"] != name:
            problems.append(
                f"0x{ident:04X} is '{entry['name']}' in {table.path.name} but "
                f"'{name}' in v141 NAMES[{label}]. FIX: reconcile in "
                f"docs/PF_VITAL_NAMES.json - v141 is byte-frozen and must not move."
            )
    return problems


if __name__ == "__main__":  # pragma: no cover - convenience self-check
    import sys

    tbl = load_names_table()
    bad_hash = tbl.hash_mismatches()
    v141_pairs = parse_v141_names()
    problems = cross_check_v141(tbl, v141_pairs)
    print(f"table  : {tbl.path} ({len(tbl)} entries)")
    print(f"v141   : {len(v141_pairs)} NAMES entries")
    print(f"hash   : {len(bad_hash)} mismatch")
    print(f"cover  : {len(problems)} problem(s)")
    for line in bad_hash:
        print(f"  HASH  {line}")
    for line in problems:
        print(f"  COVER {line}")
    sys.exit(1 if (bad_hash or problems) else 0)
