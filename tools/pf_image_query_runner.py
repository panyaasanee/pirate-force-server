#!/usr/bin/env python3
"""IMG-QUERY-001 - answer byte-level questions about the client image over a
file-based queue, so a chief WITHOUT direct access to the image can still ask
"what are the 64 bytes at 0x43BDA0" and get back a fact instead of a memory.

WHAT THIS TOOL IS FOR
---------------------
A pending directory holds ``*.query.json`` files.  Each one names a kind
(``bytes``, ``hash`` or ``search``), the sha256 the asker believes the image
has, and kind-specific args.  This runner answers every pending query in one
batch, writes ``<id>.answer.json`` into the answered directory, moves the
consumed query file next to its answer, and prints one ASCII summary line per
query.  A refusal IS an answer: the run still exits 0, because "no, and here
is the named reason" is exactly what the asker needs to correct the query.

Kinds implemented today:

  * ``bytes``   raw hex of ``length`` bytes at ``offset`` (length 1..4096);
  * ``hash``    sha256 of ``length`` bytes at ``offset`` (no upper cap);
  * ``search``  every offset where a hex pattern occurs (``bytes.find`` in a
                loop, overlap-aware), capped at ``max_hits`` with an explicit
                ``truncated`` flag.

Anything else (``strings``, ``disasm``, ``xref``, ...) is refused with
``kind_not_implemented``.  The runner NEVER interprets: no disassembly, no
guessing, no "it is probably a vtable".  It returns raw facts only; drawing
conclusions from them is the asker's job and happens in the asker's report.

WHY THE GUARDS EXIST
--------------------
A check that has never been seen red is not a check, so every guard here is a
named refusal a test deliberately triggers:

  * ``image_sha256_mismatch``   the full-file sha256 is compared to the
    asker's expected value BEFORE any bytes are read out.  On mismatch the
    answer carries ``data: null`` - never bytes - because an answer quoting
    offsets from a DIFFERENT build than the asker pinned is worse than no
    answer: it becomes false evidence with a real-looking citation.
  * ``bytes_length_over_cap`` / ``daily_byte_cap_exceeded``   per-query cap
    4096 and per-UTC-day cap 65536 on revealed bytes (``bytes`` kind only;
    ``hash`` and ``search`` reveal no bytes and do not count).  The daily
    ledger is one TSV row per successful bytes answer in
    ``<answered>/usage_log.tsv``, so the cap survives across runs.
  * ``range_outside_image``     an answer must never quote bytes the image
    does not contain.
  * ``query_malformed``         wrong types, unknown args keys, missing
    fields, or an id that is not ``[A-Za-z0-9_.-]+``.  A malformed query
    still gets an ok=false answer file, so the asker sees WHY it bounced.

NONCLAIMS
---------
The caps 4096 (per query) and 65536 (per day) are PROPOSALS for a sane review
budget, not measurements of anything; nothing was derived from them and both
are overridable (``--daily-cap-bytes`` exists for tests).  This runner makes
no claim about what any byte MEANS - it quotes, hashes and locates bytes in
one hash-pinned file, and that is the whole contract.

Usage:
    python3 tools/pf_image_query_runner.py \
        --image <path> --pending <dir> --answered <dir> \
        [--daily-cap-bytes 65536]

Exit codes: 0 = the batch ran (refusals included), 2 = unusable CLI args.
Console output is pure ASCII by construction (see ``_ascii_safe``).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BYTES_LENGTH_CAP = 4096
DEFAULT_DAILY_CAP_BYTES = 65536
SEARCH_DEFAULT_MAX_HITS = 32
SEARCH_MAX_HITS_CAP = 256

USAGE_LOG_NAME = "usage_log.tsv"
USAGE_LOG_HEADER = "date_utc\tid\tkind\tbytes_revealed"

_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_HEX64_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
_HEXSTR_RE = re.compile(r"^[0-9A-Fa-f]+$")
_ID_RECOVERY_RE = re.compile(r'"id"\s*:\s*"([A-Za-z0-9_.-]+)"')

REQUIRED_FIELDS = (
    "id", "asked_by", "subsystem", "why", "kind", "image_sha256_expected",
    "args",
)


def _ascii_safe(text: str) -> str:
    """Console lines must be pure ASCII no matter what a query file holds."""
    return "".join(ch if " " <= ch <= "~" else "?" for ch in text)


def _is_int(value) -> bool:
    """True for int but NOT bool (json true/false parse as bool in Python)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_common(query) -> str | None:
    """Structural checks shared by every kind.  Returns an error name or None."""
    if not isinstance(query, dict):
        return "query_malformed"
    for field in REQUIRED_FIELDS:
        if field not in query:
            return "query_malformed"
    if not isinstance(query["id"], str) or not _ID_RE.match(query["id"]):
        return "query_malformed"
    for field in ("asked_by", "subsystem", "why", "kind"):
        if not isinstance(query[field], str):
            return "query_malformed"
    expected = query["image_sha256_expected"]
    if not isinstance(expected, str) or not _HEX64_RE.match(expected):
        return "query_malformed"
    if not isinstance(query["args"], dict):
        return "query_malformed"
    return None


def _do_bytes(args: dict, blob: bytes, cap: int, revealed_today: int):
    """Returns (ok, data, error, bytes_revealed)."""
    if set(args) != {"offset", "length"}:
        return False, None, "query_malformed", 0
    offset, length = args["offset"], args["length"]
    if not _is_int(offset) or not _is_int(length):
        return False, None, "query_malformed", 0
    if length > BYTES_LENGTH_CAP:
        return False, None, "bytes_length_over_cap", 0
    if offset < 0 or length < 1 or offset + length > len(blob):
        return False, None, "range_outside_image", 0
    if revealed_today + length > cap:
        return False, None, "daily_byte_cap_exceeded", 0
    data = {
        "hex": blob[offset:offset + length].hex().upper(),
        "offset": offset,
        "length": length,
    }
    return True, data, None, length


def _do_hash(args: dict, blob: bytes):
    if set(args) != {"offset", "length"}:
        return False, None, "query_malformed", 0
    offset, length = args["offset"], args["length"]
    if not _is_int(offset) or not _is_int(length):
        return False, None, "query_malformed", 0
    if offset < 0 or length < 1 or offset + length > len(blob):
        return False, None, "range_outside_image", 0
    data = {
        "sha256": hashlib.sha256(blob[offset:offset + length]).hexdigest().upper(),
        "offset": offset,
        "length": length,
    }
    return True, data, None, 0


def _do_search(args: dict, blob: bytes):
    if not set(args) <= {"pattern", "max_hits"} or "pattern" not in args:
        return False, None, "query_malformed", 0
    pattern = args["pattern"]
    if (not isinstance(pattern, str) or len(pattern) % 2 != 0
            or not 2 <= len(pattern) <= 128 or not _HEXSTR_RE.match(pattern)):
        return False, None, "query_malformed", 0
    max_hits = args.get("max_hits", SEARCH_DEFAULT_MAX_HITS)
    if not _is_int(max_hits) or not 1 <= max_hits <= SEARCH_MAX_HITS_CAP:
        return False, None, "query_malformed", 0
    needle = bytes.fromhex(pattern)
    offsets = []
    truncated = False
    pos = 0
    while True:
        hit = blob.find(needle, pos)
        if hit < 0:
            break
        if len(offsets) >= max_hits:
            truncated = True  # at least one more hit exists beyond the cap
            break
        offsets.append(hit)
        pos = hit + 1  # overlap-aware on purpose: raw facts, no editing
    data = {"offsets": offsets, "count": len(offsets), "truncated": truncated}
    return True, data, None, 0


def _load_today_usage(log_path: Path, today: str) -> int:
    """Sum of bytes_revealed already logged for TODAY (UTC)."""
    total = 0
    if not log_path.is_file():
        return total
    for line in log_path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) != 4 or parts[0] == "date_utc" or parts[0] != today:
            continue
        try:
            total += int(parts[3])
        except ValueError:
            continue
    return total


def _append_usage(log_path: Path, today: str, query_id: str, length: int) -> None:
    fresh = not log_path.exists()
    with open(log_path, "a", encoding="utf-8", newline="") as handle:
        if fresh:
            handle.write(USAGE_LOG_HEADER + "\n")
        handle.write("%s\t%s\t%s\t%d\n" % (today, query_id, "bytes", length))


def _answer_query(query, blob: bytes, sha_actual: str, cap: int,
                  revealed_today: int):
    """Decide one already-parsed query.  Returns (ok, data, error, revealed).

    Guard order is deliberate: structure first, then the sha pin (nothing is
    ever computed against an image the asker did not pin), then the kind.
    """
    error = _validate_common(query)
    if error is not None:
        return False, None, error, 0
    if query["image_sha256_expected"].upper() != sha_actual:
        return False, None, "image_sha256_mismatch", 0
    kind = query["kind"]
    if kind == "bytes":
        return _do_bytes(query["args"], blob, cap, revealed_today)
    if kind == "hash":
        return _do_hash(query["args"], blob)
    if kind == "search":
        return _do_search(query["args"], blob)
    return False, None, "kind_not_implemented", 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Answer pending image byte-level queries (batch mode).")
    parser.add_argument("--image", required=True,
                        help="path to the read-only client image")
    parser.add_argument("--pending", required=True,
                        help="directory holding *.query.json files")
    parser.add_argument("--answered", required=True,
                        help="directory for answers, consumed queries and "
                             "usage_log.tsv")
    parser.add_argument("--daily-cap-bytes", type=int,
                        default=DEFAULT_DAILY_CAP_BYTES,
                        help="daily revealed-bytes cap (tests only; default "
                             "%(default)s)")
    args = parser.parse_args(argv)

    image = Path(args.image)
    pending = Path(args.pending)
    answered = Path(args.answered)
    if not image.is_file():
        print("ERROR image not found: %s" % _ascii_safe(str(image)),
              file=sys.stderr)
        return 2
    if not pending.is_dir():
        print("ERROR pending dir not found: %s" % _ascii_safe(str(pending)),
              file=sys.stderr)
        return 2
    if args.daily_cap_bytes < 1:
        print("ERROR --daily-cap-bytes must be >= 1", file=sys.stderr)
        return 2
    answered.mkdir(parents=True, exist_ok=True)

    blob = image.read_bytes()  # hashed and searched ONCE per run
    sha_actual = hashlib.sha256(blob).hexdigest().upper()
    log_path = answered / USAGE_LOG_NAME
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    revealed_today = _load_today_usage(log_path, today)

    answered_count = 0
    refused_count = 0
    for query_file in sorted(pending.glob("*.query.json"),
                             key=lambda path: path.name):
        started = time.perf_counter()
        query = None
        query_id = None
        kind = None
        ok = False
        data = None
        error = None
        revealed = 0
        raw = query_file.read_text(encoding="utf-8", errors="replace")
        try:
            query = json.loads(raw)
        except ValueError:
            error = "query_malformed"
            match = _ID_RECOVERY_RE.search(raw)
            if match:
                query_id = match.group(1)
        if error is None:
            if isinstance(query, dict):
                candidate = query.get("id")
                if isinstance(candidate, str) and _ID_RE.match(candidate):
                    query_id = candidate
                if isinstance(query.get("kind"), str):
                    kind = query["kind"]
            ok, data, error, revealed = _answer_query(
                query, blob, sha_actual, args.daily_cap_bytes, revealed_today)
        elapsed = time.perf_counter() - started
        answer = {
            "id": query_id,
            "answered_at": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "elapsed_seconds": elapsed,
            "image_sha256_actual": sha_actual,
            "ok": ok,
            "data": data,
            "error": error,
            "query_verbatim": query,
        }
        answer_name = ((query_id if query_id else query_file.name)
                       + ".answer.json")
        (answered / answer_name).write_text(
            json.dumps(answer, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        destination = answered / query_file.name
        if destination.exists():
            destination.unlink()
        shutil.move(str(query_file), str(destination))
        if ok and revealed:
            _append_usage(log_path, today, query_id, revealed)
            revealed_today += revealed
        if ok:
            answered_count += 1
        else:
            refused_count += 1
        print("ANSWERED %s kind=%s ok=%d elapsed=%.3f"
              % (_ascii_safe(query_id if query_id else query_file.name),
                 _ascii_safe(kind if kind else "unknown"),
                 1 if ok else 0, elapsed))
    print("DONE answered=%d refused=%d" % (answered_count, refused_count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
