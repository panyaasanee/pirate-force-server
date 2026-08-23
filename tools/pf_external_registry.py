#!/usr/bin/env python3
"""EXTERNAL-RE-READER-001 - the first code that reads the Codex RE deliverable.

WHAT THIS IS
------------
../pf_bridge/external/ holds the frozen deliverable tables of the Codex static
RE pass (2026-08-23): every wire message the client registers, with VAs, file
offsets, serializer field lists, spans and span sha256s.  Panya ruled on
2026-08-23 20:39 (+07:00) that the tables go on the remote as-is (they carry
derived metadata and short compiler-boilerplate byte strings, not the image),
and the bridge merged them to pf_bridge main the same evening.  Until this tool
existed, NOT ONE line of src/, tools/ or tests/ read those files - Panya asked
(order 2026-08-23 18:22, item 5) that this gap be a visible work item instead
of a silent one.  This module closes it.

WHAT IT DOES
------------
1. Loads the five committed tables STRICTLY: exact header, exact row count,
   exact file sha256, ASCII-only bytes.  Any deviation raises; there is no
   "best effort" mode.  The pins mean "the tables this code was written
   against"; when the bridge regenerates the deliverable the pins move in the
   same commit as the code that re-read them - never silently.
2. Answers the two questions rounds actually ask (the same ones
   pf_bridge/external/00_SEARCH_HERE_FIRST.md answers by hand):
     * --message NAME: the registry row plus every serializer field row.
     * --stats: table counts and the cross-check summary.
3. --verify: re-checks every cross-table invariant measured on 2026-08-23
   (see CROSS-CHECKS below) plus the file sha256 pins.
4. --verify-spans IMAGE: hashes every distinct serializer span out of a client
   image and compares against span_sha256.  This is the only mode that needs
   the image, so it is the only mode that cannot run on the cloud clone; when
   the image path is missing the tool REFUSES (exit 3) instead of pretending.

CROSS-CHECKS (all measured against the 2026-08-23 tables, all exact)
--------------------------------------------------------------------
  * registry and serializer tables name exactly the same 519 messages;
  * per (message, direction) the field `order` runs 1..n with no gap;
  * section deltas are uniform: every known code VA sits at file offset
    va - 0x400C00 (reg_site 519/519, getter 504/504 known) and every known
    data VA at va - 0x401C00 (name 519/519, vtable 502/502 known);
  * every field row's file_off_claim maps back INSIDE its own span;
  * the 16 messages whose registry serializer_va is UNKNOWN are exactly the
    16 whose 32 field rows (W and R) carry no span - nobody else is spanless.

WHAT THIS TOOL DOES NOT CLAIM
-----------------------------
  * It does not claim the tables are TRUE.  They are another agent's derived
    work; the standing rule is verify span_sha256 against the real image
    before relying on any row, and the image only exists on the bridge.
    --verify (no image) checks internal consistency, not ground truth.
  * It does not claim field meaning or direction-in-practice.  A W row means
    the serializer can write the field, not that the client ever sends it
    (00_SEARCH_HERE_FIRST.md, limitation 1).
  * field_offset and len are exposed as the strings the deliverable wrote
    (+0x14, DEREF(...), STACK@..., N/A, 4+N_bytes).  Only 1,726 of 6,931 rows
    are a plain +0x offset; parsing the rest is future work, not this tool
    quietly guessing.

ASCII only, on purpose: the bridge console is code page 874.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_DIR = ROOT.parent / "pf_bridge" / "external"

# Section mapping constants, measured 2026-08-23 across every known VA/offset
# pair in PF_PROTOCOL_REGISTRY.tsv (see CROSS-CHECKS in the module docstring).
# 32-bit image, no ASLR relevance: the tables store preferred-base VAs.
CODE_DELTA = 0x400C00  # .text:  va = file_off + CODE_DELTA
DATA_DELTA = 0x401C00  # .rdata/.data: va = file_off + DATA_DELTA

UNKNOWN = "UNKNOWN"

# The pf_bridge commit whose external/ tree every pin below was measured
# against.  The sha pins bind CONTENT; this binds the REVISION, so when the
# bridge regenerates the deliverable and a fresh clone goes red on the sha
# pins, this repository alone can still answer "which deliverable was the
# code written against" (adversary finding, round R131).
PF_BRIDGE_PIN_COMMIT = "284d98667080e89407120f2b298ba47532449a31"

# ---------------------------------------------------------------------------
# Pins: the deliverable snapshot this module was written against.
# To re-pin after the bridge regenerates the tables: run
#   py -3 tools/pf_external_registry.py --measure
# and update PINS in the same commit as whatever consumed the new tables.
# ---------------------------------------------------------------------------

PINS = {
    "PF_PROTOCOL_REGISTRY.tsv": {
        "rows": 519,
        "sha256": "27daac0c6fbbc45d88281c31b98e3a8b56f421bd1e8bc16f970fdff5716cfb4d",
        "header": (
            "name", "name_va", "reg_site_va", "id_global_va", "getter_va",
            "vtable_va", "serializer_va", "handler_va", "file_off_reg",
            "file_off_name", "file_off_getter", "file_off_vtable",
            "file_off_serializer_ptr", "file_off_handler_ptr", "source",
        ),
    },
    "PF_SERIALIZER_FIELDS.tsv": {
        "rows": 6931,
        "sha256": "99282bdf3f492eaebdbab4918aecc0e37bf8efb42b904b18e1ba306767b5c123",
        "header": (
            "message", "direction(W/R)", "order", "tag", "field_offset",
            "len", "gate_condition", "span_start", "span_end", "span_sha256",
            "file_off_claim", "source",
        ),
    },
    "PF_RUNTIME_CLASSMAP.tsv": {
        "rows": 6244,
        "sha256": "c53a6eaf23911765ebabd5e86ccaecf827ffdd88a1f514fc3f0f3ea2c3484985",
        "header": (
            "record_kind", "vtable_va", "class_name", "type_descriptor_name",
            "instance_count", "type_descriptor_va", "type_descriptor_count",
            "type_info_vtable_va", "object_offset", "dump_name", "dump_sha256",
            "dump_file_offset", "instance_file_offsets", "rtti_status",
            "source",
        ),
    },
    "PF_FIELD_VALIDATION.tsv": {
        "rows": 1038,
        "sha256": "080a5f32580df575632fee69d3f8faa6e2e745ad1775d05daf3e272e4e0941c3",
        "header": (
            "message", "direction(W/R)", "observed_frames",
            "observed_instances", "parse_success_frames",
            "parse_success_instances", "a2_static_open_frames",
            "a2_static_open_instances", "mismatch_frames",
            "mismatch_instances", "mismatch_field_index_reason_count",
            "capture_file_count", "status", "source",
        ),
    },
    "PF_INPUT_INVENTORY.tsv": {
        "rows": 2066,
        "sha256": "729b5e73383de8fd6e0008875d4b9b685de2ad8d72a55118aa862093f10259d1",
        "header": ("source", "source_id", "relative_path", "size", "sha256",
                   "role"),
    },
}

# Cross-check pins (counts measured 2026-08-23; see module docstring).
MESSAGE_COUNT = 519
FIELD_GROUPS = 1038            # 519 messages x 2 directions, all present
UNKNOWN_SERIALIZER_MESSAGES = 16
SPANLESS_FIELD_ROWS = 32       # exactly the W+R rows of those 16 messages
EMPTY_TAG_ROWS = 202           # tag == EMPTY, every one carries a real span
KNOWN_GETTER_ROWS = 504        # 519 - 15 UNKNOWN getters
KNOWN_VTABLE_ROWS = 502        # 519 - 17 UNKNOWN vtables


class ExternalRegistryError(RuntimeError):
    """Any deviation between the tables and what this module pins."""


def _fail(msg):
    raise ExternalRegistryError(msg)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def external_dir_present(base=None):
    base = Path(base) if base is not None else EXTERNAL_DIR
    return all((base / name).is_file() for name in PINS)


def _read_strict(path, pin, check_sha=True):
    raw = path.read_bytes()
    for i, byte in enumerate(raw):
        if byte > 0x7F:
            _fail("%s: non-ASCII byte 0x%02X at offset %d" % (path.name, byte, i))
    if b"\r" in raw:
        _fail("%s: CR byte present, tables are LF-only" % path.name)
    if check_sha:
        digest = hashlib.sha256(raw).hexdigest()
        if digest != pin["sha256"]:
            _fail("%s: sha256 %s does not match pin %s - the deliverable "
                  "moved; re-measure and re-pin in the same commit"
                  % (path.name, digest, pin["sha256"]))
    lines = list(csv.reader(raw.decode("ascii").splitlines(), delimiter="\t"))
    if not lines:
        _fail("%s: empty file" % path.name)
    header = tuple(lines[0])
    if header != pin["header"]:
        _fail("%s: header %r does not match pin" % (path.name, header))
    rows = lines[1:]
    if len(rows) != pin["rows"]:
        _fail("%s: %d data rows, pin says %d" % (path.name, len(rows), pin["rows"]))
    width = len(header)
    for n, row in enumerate(rows, start=2):
        if len(row) != width:
            _fail("%s line %d: %d cells, header has %d" % (path.name, n, len(row), width))
    return header, rows


def load_table(name, base=None, check_sha=True):
    """(header, rows) for one pinned table, or raise ExternalRegistryError."""
    if name not in PINS:
        _fail("unknown table %r; pinned tables: %s" % (name, ", ".join(sorted(PINS))))
    base = Path(base) if base is not None else EXTERNAL_DIR
    path = base / name
    if not path.is_file():
        _fail("%s is not present at %s - on the cloud this means the "
              "pf_bridge sibling clone is missing or stale" % (name, path))
    return _read_strict(path, PINS[name], check_sha=check_sha)


def _dicts(header, rows):
    return [dict(zip(header, row)) for row in rows]


def protocol_registry(base=None, check_sha=True):
    """name -> registry row dict, exactly MESSAGE_COUNT entries."""
    header, rows = load_table("PF_PROTOCOL_REGISTRY.tsv", base, check_sha)
    out = {}
    for row in _dicts(header, rows):
        if row["name"] in out:
            _fail("duplicate registry name %r" % row["name"])
        out[row["name"]] = row
    return out


def serializer_fields(base=None, check_sha=True):
    """Every field row as a dict, in file order."""
    header, rows = load_table("PF_SERIALIZER_FIELDS.tsv", base, check_sha)
    return _dicts(header, rows)


def fields_for(message, direction=None, base=None, check_sha=True):
    rows = [r for r in serializer_fields(base, check_sha) if r["message"] == message]
    if direction is not None:
        rows = [r for r in rows if r["direction(W/R)"] == direction]
    return rows


def _hex(value, what="cell"):
    """int(value, 16), None for UNKNOWN, or a LOUD refusal - never a traceback.

    The adversary pass (R131) fed a mutated cell through the first draft and
    got a raw ValueError, which breaks the tool's own refusal contract.  Any
    cell that is neither UNKNOWN nor hex is a table defect and must say so.
    """
    if value == UNKNOWN:
        return None
    try:
        return int(value, 16)
    except ValueError:
        _fail("%s: %r is neither UNKNOWN nor a hex number" % (what, value))


def _int(value, what):
    try:
        return int(value)
    except ValueError:
        _fail("%s: %r is not a decimal integer" % (what, value))


_HEX_DIGITS = frozenset("0123456789abcdef")


def _check_hex_or_unknown(value, what, allow_pipe=False):
    """Format gate for a registry cell: UNKNOWN, hex, or (if allowed) a
    pipe-separated hex list - the deliverable really ships 0x..|0x.. cells in
    the two _ptr columns, measured 2 rows each."""
    if value == UNKNOWN:
        return
    parts = value.split("|") if allow_pipe else [value]
    if len(parts) > 1 and not allow_pipe:
        _fail("%s: %r is multi-valued where a single value is pinned" % (what, value))
    for part in parts:
        _hex(part, what)


# ---------------------------------------------------------------------------
# Cross-checks
# ---------------------------------------------------------------------------

def cross_check(base=None, check_sha=True):
    """Verify every pinned invariant; return the measured summary dict."""
    registry = protocol_registry(base, check_sha)
    fields = serializer_fields(base, check_sha)

    if len(registry) != MESSAGE_COUNT:
        _fail("registry names %d messages, pin says %d" % (len(registry), MESSAGE_COUNT))

    # Format gate over EVERY registry cell, so a column nothing delta-checks
    # (serializer_va, handler_va, id_global_va, the _ptr pair) still cannot
    # rot silently once the sha pin legitimately moves (adversary, R131).
    PIPE_COLUMNS = ("file_off_serializer_ptr", "file_off_handler_ptr")
    pipe_cells = Counter()
    for name, row in registry.items():
        for col, value in row.items():
            if col in ("name", "source"):
                continue
            _check_hex_or_unknown(value, "%s.%s" % (name, col),
                                  allow_pipe=col in PIPE_COLUMNS)
            if "|" in value:
                pipe_cells[col] += 1
    for col in PIPE_COLUMNS:
        if pipe_cells[col] != 2:
            _fail("%s: %d pipe-valued cells, pin says 2" % (col, pipe_cells[col]))

    reg_names = set(registry)
    ser_names = set(r["message"] for r in fields)
    if ser_names != reg_names:
        _fail("name join broken: %d only-serializer, %d only-registry"
              % (len(ser_names - reg_names), len(reg_names - ser_names)))

    # order contiguity per (message, direction)
    groups = {}
    for row in fields:
        groups.setdefault((row["message"], row["direction(W/R)"]), []).append(row)
    if len(groups) != FIELD_GROUPS:
        _fail("%d (message,direction) groups, pin says %d" % (len(groups), FIELD_GROUPS))
    for key, rows in groups.items():
        orders = sorted(_int(r["order"], "%r order" % (key,)) for r in rows)
        if orders != list(range(1, len(orders) + 1)):
            _fail("order not contiguous for %r: %r" % (key, orders))

    # uniform section deltas over every KNOWN va/offset pair
    def delta_check(va_col, off_col, expect, expect_known):
        known = 0
        for row in registry.values():
            va, off = _hex(row[va_col]), _hex(row[off_col])
            if va is None or off is None:
                continue
            known += 1
            if va - off != expect:
                _fail("%s: %s - %s = 0x%X, expected 0x%X"
                      % (row["name"], va_col, off_col, va - off, expect))
        if known != expect_known:
            _fail("%s: %d known rows, pin says %d" % (va_col, known, expect_known))

    delta_check("reg_site_va", "file_off_reg", CODE_DELTA, MESSAGE_COUNT)
    delta_check("getter_va", "file_off_getter", CODE_DELTA, KNOWN_GETTER_ROWS)
    delta_check("name_va", "file_off_name", DATA_DELTA, MESSAGE_COUNT)
    delta_check("vtable_va", "file_off_vtable", DATA_DELTA, KNOWN_VTABLE_ROWS)

    # spanless rows are exactly the UNKNOWN-serializer messages, and every
    # row that has a span keeps its own claim site inside that span
    unknown_serializer = set(
        name for name, row in registry.items() if row["serializer_va"] == UNKNOWN
    )
    if len(unknown_serializer) != UNKNOWN_SERIALIZER_MESSAGES:
        _fail("%d UNKNOWN-serializer messages, pin says %d"
              % (len(unknown_serializer), UNKNOWN_SERIALIZER_MESSAGES))

    spanless = 0
    empty_tag = 0
    for row in fields:
        where = "%s/%s #%s" % (row["message"], row["direction(W/R)"], row["order"])
        start = _hex(row["span_start"], where + " span_start")
        end = _hex(row["span_end"], where + " span_end")
        claim = _hex(row["file_off_claim"], where + " file_off_claim")
        if start is None or end is None or claim is None:
            spanless += 1
            if row["message"] not in unknown_serializer:
                _fail("%s has a spanless field row but a known serializer"
                      % row["message"])
            continue
        if row["tag"] == "EMPTY":
            empty_tag += 1
        if not start < end:
            _fail("%s: span [0x%X, 0x%X) is not increasing"
                  % (row["message"], start, end))
        mapped = claim + CODE_DELTA
        if not start <= mapped < end:
            _fail("%s: claim 0x%X maps to 0x%X, outside span [0x%X, 0x%X)"
                  % (row["message"], claim, mapped, start, end))
        sha = row["span_sha256"]
        if len(sha) != 64 or not set(sha) <= _HEX_DIGITS:
            _fail("%s: span_sha256 %r is not 64 lowercase hex chars"
                  % (row["message"], sha))
    if spanless != SPANLESS_FIELD_ROWS:
        _fail("%d spanless field rows, pin says %d" % (spanless, SPANLESS_FIELD_ROWS))
    if empty_tag != EMPTY_TAG_ROWS:
        _fail("%d EMPTY-tag rows, pin says %d" % (empty_tag, EMPTY_TAG_ROWS))

    directions = Counter(r["direction(W/R)"] for r in fields)
    return {
        "messages": len(registry),
        "field_rows": len(fields),
        "field_groups": len(groups),
        "directions": dict(directions),
        "unknown_serializer_messages": len(unknown_serializer),
        "spanless_field_rows": spanless,
        "empty_tag_rows": empty_tag,
        "distinct_spans": len(set(
            (r["span_start"], r["span_end"], r["span_sha256"])
            for r in fields if r["span_start"] != UNKNOWN
        )),
    }


# ---------------------------------------------------------------------------
# Span verification against a client image (bridge-only)
# ---------------------------------------------------------------------------

def verify_spans(image_path, base=None, check_sha=True):
    """Hash every distinct span out of the image; return the verdict dict.

    The mapping used is file_off = span_va - CODE_DELTA, the same uniform
    .text delta the registry pins.  A span whose mapped range falls outside
    the file is reported as unreadable, never silently skipped.
    """
    image = Path(image_path)
    if not image.is_file():
        _fail("client image %s is not present - span verification only "
              "runs on the bridge" % image)
    blob = image.read_bytes()
    spans = {}
    for row in serializer_fields(base, check_sha):
        if row["span_start"] == UNKNOWN:
            continue
        key = (row["span_start"], row["span_end"], row["span_sha256"])
        spans.setdefault(key, row["message"])
    verified, mismatched, unreadable = [], [], []
    for (start_s, end_s, want), message in sorted(spans.items()):
        start, end = int(start_s, 16), int(end_s, 16)
        off = start - CODE_DELTA
        length = end - start
        if off < 0 or off + length > len(blob):
            unreadable.append((message, start_s, end_s))
            continue
        got = hashlib.sha256(blob[off:off + length]).hexdigest()
        (verified if got == want else mismatched).append((message, start_s, end_s))
    return {
        "image": str(image),
        "image_sha256": hashlib.sha256(blob).hexdigest(),
        "distinct_spans": len(spans),
        "verified": len(verified),
        "mismatched": len(mismatched),
        "unreadable": len(unreadable),
        "mismatched_spans": mismatched[:20],
        "unreadable_spans": unreadable[:20],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_message(name, base, check_sha):
    registry = protocol_registry(base, check_sha)
    if name not in registry:
        print("NOT FOUND: %s is not one of the %d registered messages"
              % (name, len(registry)))
        return 1
    row = registry[name]
    for col in PINS["PF_PROTOCOL_REGISTRY.tsv"]["header"]:
        print("  %-24s %s" % (col, row[col]))
    for direction in ("W", "R"):
        rows = fields_for(name, direction, base, check_sha)
        print("  fields %s: %d" % (direction, len(rows)))
        for f in rows:
            print("    #%s tag %s @ %s len %s span [%s,%s) gate %s"
                  % (f["order"], f["tag"], f["field_offset"], f["len"],
                     f["span_start"], f["span_end"],
                     f["gate_condition"][:60]))
    return 0


def _measure(base):
    """Print current pins for every table (for re-pinning after a regen)."""
    print("measured against pf_bridge commit %s (update PF_BRIDGE_PIN_COMMIT "
          "when re-pinning)" % PF_BRIDGE_PIN_COMMIT)
    for name in sorted(PINS):
        path = (Path(base) if base is not None else EXTERNAL_DIR) / name
        raw = path.read_bytes()
        rows = len(raw.decode("ascii", errors="replace").splitlines()) - 1
        print("%s rows=%d sha256=%s" % (name, rows, hashlib.sha256(raw).hexdigest()))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read, query and verify the Codex RE deliverable tables "
                    "in ../pf_bridge/external/ (see module docstring).")
    parser.add_argument("--base", default=None,
                        help="override the external/ directory (tests only)")
    parser.add_argument("--no-sha", action="store_true",
                        help="skip the file sha256 pins (tests only; every "
                             "other check still runs)")
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--message", metavar="NAME")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--verify-spans", metavar="IMAGE")
    parser.add_argument("--measure", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    check_sha = not args.no_sha

    if not external_dir_present(args.base):
        print("REFUSED: the deliverable tables are not present at %s"
              % (args.base or EXTERNAL_DIR))
        print("         on the cloud clone this means pf_bridge was not "
              "cloned beside this repository")
        return 3

    try:
        if args.measure:
            return _measure(args.base)
        # `is not None`, never truthiness: an empty-string argument (an unset
        # %VAR% in a bridge batch file) must not fall through to a different
        # mode and answer the wrong question with exit 0 (adversary, R131).
        if args.message is not None:
            if not args.message:
                print("REFUSED: --message got an empty string")
                return 3
            return _print_message(args.message, args.base, check_sha)
        if args.verify_spans is not None:
            if not args.verify_spans:
                print("REFUSED: --verify-spans got an empty image path")
                return 3
            image = Path(args.verify_spans)
            if not image.is_file():
                print("REFUSED: client image %s is not present - this mode "
                      "only runs on the bridge" % image)
                return 3
            verdict = verify_spans(image, args.base, check_sha)
            print(json.dumps(verdict, indent=2) if args.json else
                  "spans=%(distinct_spans)d verified=%(verified)d "
                  "mismatched=%(mismatched)d unreadable=%(unreadable)d" % verdict)
            return 0 if verdict["mismatched"] == 0 and verdict["unreadable"] == 0 else 1
        # --stats and --verify both run the full cross-check; --stats without
        # --verify still refuses to print numbers a broken table produced.
        summary = cross_check(args.base, check_sha)
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            for key in sorted(summary):
                print("%-28s %s" % (key, summary[key]))
            print("pinned against pf_bridge commit %s" % PF_BRIDGE_PIN_COMMIT)
            print("cross-check: OK (every pinned invariant held)")
        return 0
    except ExternalRegistryError as error:
        print("FAILED: %s" % error)
        return 1
    except Exception as error:  # noqa: BLE001 - refusal contract backstop
        # A traceback is not a refusal.  Anything unexpected still exits 1
        # with a FAILED line a bridge batch file can grep (adversary, R131).
        print("FAILED: unexpected %s: %s" % (type(error).__name__, error))
        return 1


if __name__ == "__main__":
    sys.exit(main())
