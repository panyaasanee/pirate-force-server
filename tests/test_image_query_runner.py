"""IMG-QUERY-001 - prove every named refusal in the image query runner fires,
on a throwaway image - never on the real client binary.

``tools/pf_image_query_runner.py`` answers ``bytes`` / ``hash`` / ``search``
queries against a hash-pinned image, and refuses everything else with a named
snake_case error.  A check that has never been seen red is not a check, so
each guard here is driven through its red path on purpose:

  * ``image_sha256_mismatch``   must yield data=null and leak NOT ONE hex
    digit of the real bytes into the answer file;
  * ``bytes_length_over_cap``   length 4097 bounces and logs no usage row;
  * ``daily_byte_cap_exceeded`` a shrunken --daily-cap-bytes shows the ledger
    actually stops the second query WITHIN the same run;
  * ``range_outside_image``     a read crossing EOF bounces;
  * ``kind_not_implemented``    ``disasm`` is refused, not attempted;
  * ``query_malformed``         an unknown args key bounces, and a file that
    is not even JSON still produces an ok=false answer file.

The happy paths are cross-checked against independent stdlib math (slicing
plus hashlib on the same temp image), and one subprocess run proves the
console stays pure ASCII even when a query's "why" field is Thai - the Thai
survives inside the utf-8 answer JSON (data), never on stdout (console).

None of this needs the real client image: every test builds an 8192-byte
deterministic pattern in a temp directory.  These tests import nothing from
``src/``, open no socket, touch no database and launch no GameClient.

Run just this file:
    python3 -m pytest tests/test_image_query_runner.py -q
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "pf_image_query_runner.py"

_TOOL_MODULE = None

# Planted so ``search`` has known ground truth.  The base pattern below steps
# by 7 between consecutive bytes; the needle steps by 0x11, so it cannot occur
# anywhere except where we plant it.
NEEDLE_HEX = "AABBCCDDEEFF"
NEEDLE_OFFSETS = (100, 3000, 8000)
IMAGE_SIZE = 8192

ANSWER_KEYS = {
    "id", "answered_at", "kind", "elapsed_seconds", "image_sha256_actual",
    "ok", "data", "error", "query_verbatim",
}

# Thai for "test the Thai language", spelled with escapes so this source file
# stays 100% ASCII (the console gate scans tests/ too).
THAI_WHY = ("\u0e17\u0e14\u0e2a\u0e2d\u0e1a"
            "\u0e20\u0e32\u0e29\u0e32\u0e44\u0e17\u0e22")


def load_tool():
    global _TOOL_MODULE
    if _TOOL_MODULE is None:
        spec = importlib.util.spec_from_file_location("pf_image_query_runner", TOOL)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        _TOOL_MODULE = module
    return _TOOL_MODULE


def build_image() -> bytes:
    base = bytearray((i * 7 + 3) % 256 for i in range(IMAGE_SIZE))
    needle = bytes.fromhex(NEEDLE_HEX)
    for offset in NEEDLE_OFFSETS:
        base[offset:offset + len(needle)] = needle
    return bytes(base)


class Harness:
    """One temp image + pending/answered pair per test."""

    def __init__(self, tmp: str) -> None:
        root = Path(tmp)
        self.image_bytes = build_image()
        self.image = root / "image.bin"
        self.image.write_bytes(self.image_bytes)
        self.sha = hashlib.sha256(self.image_bytes).hexdigest().upper()
        self.pending = root / "pending"
        self.answered = root / "answered"
        self.pending.mkdir()
        self.answered.mkdir()

    def add_query(self, query_id: str, kind: str, args: dict,
                  sha: str | None = None, why: str = "unit test",
                  filename: str | None = None) -> Path:
        query = {
            "id": query_id,
            "asked_by": "test_image_query_runner",
            "subsystem": "img_query",
            "why": why,
            "kind": kind,
            "image_sha256_expected": self.sha if sha is None else sha,
            "args": args,
        }
        path = self.pending / (filename or (query_id + ".query.json"))
        path.write_text(json.dumps(query, indent=2, ensure_ascii=False),
                        encoding="utf-8")
        return path

    def run(self, extra=()):  # returns (exit_code, stdout_text)
        argv = ["--image", str(self.image), "--pending", str(self.pending),
                "--answered", str(self.answered)] + list(extra)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = load_tool().main(argv)
        return code, buffer.getvalue()

    def answer(self, query_id: str) -> dict:
        path = self.answered / (query_id + ".answer.json")
        return json.loads(path.read_text(encoding="utf-8"))

    def answer_text(self, query_id: str) -> str:
        path = self.answered / (query_id + ".answer.json")
        return path.read_text(encoding="utf-8")

    def usage_rows(self) -> list:
        path = self.answered / "usage_log.tsv"
        if not path.is_file():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) == 4 and parts[0] != "date_utc":
                rows.append(parts)
        return rows


class HappyPathTests(unittest.TestCase):
    """Green answers are cross-checked against independent stdlib math."""

    def test_bytes_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Harness(tmp)
            box.add_query("q_bytes_001", "bytes", {"offset": 200, "length": 16})
            code, out = box.run()
            self.assertEqual(code, 0)
            self.assertIn("ANSWERED q_bytes_001 kind=bytes ok=1", out)
            self.assertIn("DONE answered=1 refused=0", out)
            answer = box.answer("q_bytes_001")
            self.assertEqual(set(answer), ANSWER_KEYS)
            self.assertTrue(answer["ok"])
            self.assertIsNone(answer["error"])
            self.assertEqual(answer["kind"], "bytes")
            self.assertEqual(answer["image_sha256_actual"], box.sha)
            self.assertIsInstance(answer["elapsed_seconds"], float)
            self.assertIn("+00:00", answer["answered_at"])
            expected_hex = box.image_bytes[200:216].hex().upper()
            self.assertEqual(answer["data"],
                             {"hex": expected_hex, "offset": 200, "length": 16})
            self.assertEqual(answer["data"]["hex"],
                             answer["data"]["hex"].upper())
            self.assertEqual(answer["query_verbatim"]["id"], "q_bytes_001")
            # consumed: gone from pending, parked next to its answer
            self.assertFalse((box.pending / "q_bytes_001.query.json").exists())
            self.assertTrue((box.answered / "q_bytes_001.query.json").exists())
            rows = box.usage_rows()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][1:], ["q_bytes_001", "bytes", "16"])

    def test_hash_happy_path_does_not_touch_the_byte_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Harness(tmp)
            box.add_query("q_hash_001", "hash", {"offset": 32, "length": 5000})
            code, _ = box.run()
            self.assertEqual(code, 0)
            answer = box.answer("q_hash_001")
            self.assertTrue(answer["ok"])
            expected = hashlib.sha256(
                box.image_bytes[32:5032]).hexdigest().upper()
            self.assertEqual(answer["data"],
                             {"sha256": expected, "offset": 32, "length": 5000})
            # hash reveals no bytes, so the daily ledger must stay empty
            self.assertEqual(box.usage_rows(), [])

    def test_search_finds_all_planted_needles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Harness(tmp)
            box.add_query("q_search_all", "search", {"pattern": NEEDLE_HEX})
            code, _ = box.run()
            self.assertEqual(code, 0)
            answer = box.answer("q_search_all")
            self.assertTrue(answer["ok"])
            self.assertEqual(answer["data"],
                             {"offsets": list(NEEDLE_OFFSETS), "count": 3,
                              "truncated": False})

    def test_search_max_hits_truncates_honestly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Harness(tmp)
            box.add_query("q_search_cap", "search",
                          {"pattern": NEEDLE_HEX, "max_hits": 2})
            code, _ = box.run()
            self.assertEqual(code, 0)
            answer = box.answer("q_search_cap")
            self.assertTrue(answer["ok"])
            self.assertEqual(answer["data"],
                             {"offsets": list(NEEDLE_OFFSETS[:2]), "count": 2,
                              "truncated": True})


class TrapTests(unittest.TestCase):
    """Every named refusal must be seen red, by name."""

    def test_sha_mismatch_reveals_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Harness(tmp)
            wrong_sha = hashlib.sha256(b"a different build").hexdigest()
            box.add_query("q_trap_sha", "bytes",
                          {"offset": 200, "length": 32}, sha=wrong_sha)
            code, out = box.run()
            self.assertEqual(code, 0)  # a refusal is a correct answer
            self.assertIn("ok=0", out)
            answer = box.answer("q_trap_sha")
            self.assertFalse(answer["ok"])
            self.assertEqual(answer["error"], "image_sha256_mismatch")
            self.assertIsNone(answer["data"])
            # the real bytes must appear NOWHERE in the answer, any case
            real_hex = box.image_bytes[200:232].hex().upper()
            self.assertNotIn(real_hex, box.answer_text("q_trap_sha").upper())

    def test_bytes_length_over_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Harness(tmp)
            box.add_query("q_trap_cap", "bytes", {"offset": 0, "length": 4097})
            code, _ = box.run()
            self.assertEqual(code, 0)
            answer = box.answer("q_trap_cap")
            self.assertFalse(answer["ok"])
            self.assertEqual(answer["error"], "bytes_length_over_cap")
            self.assertIsNone(answer["data"])
            self.assertEqual(box.usage_rows(), [])

    def test_daily_byte_cap_stops_the_second_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Harness(tmp)
            # sorted by filename, so 001 is answered before 002
            box.add_query("q_cap_001", "bytes", {"offset": 0, "length": 64})
            box.add_query("q_cap_002", "bytes", {"offset": 512, "length": 64})
            code, out = box.run(extra=["--daily-cap-bytes", "100"])
            self.assertEqual(code, 0)
            self.assertIn("DONE answered=1 refused=1", out)
            first = box.answer("q_cap_001")
            self.assertTrue(first["ok"])
            self.assertEqual(first["data"]["hex"],
                             box.image_bytes[0:64].hex().upper())
            second = box.answer("q_cap_002")
            self.assertFalse(second["ok"])
            self.assertEqual(second["error"], "daily_byte_cap_exceeded")
            self.assertIsNone(second["data"])
            rows = box.usage_rows()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][1], "q_cap_001")

    def test_kind_disasm_is_refused_not_attempted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Harness(tmp)
            box.add_query("q_trap_disasm", "disasm", {"offset": 0, "length": 16})
            code, _ = box.run()
            self.assertEqual(code, 0)
            answer = box.answer("q_trap_disasm")
            self.assertFalse(answer["ok"])
            self.assertEqual(answer["error"], "kind_not_implemented")
            self.assertIsNone(answer["data"])

    def test_unknown_args_key_is_malformed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Harness(tmp)
            box.add_query("q_trap_extra", "bytes",
                          {"offset": 0, "length": 16, "and_also": "this"})
            code, _ = box.run()
            self.assertEqual(code, 0)
            answer = box.answer("q_trap_extra")
            self.assertFalse(answer["ok"])
            self.assertEqual(answer["error"], "query_malformed")
            self.assertIsNone(answer["data"])

    def test_invalid_json_still_gets_an_answer_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Harness(tmp)
            (box.pending / "broken.query.json").write_text(
                "{ this is not json", encoding="utf-8")
            code, out = box.run()
            self.assertEqual(code, 0)
            self.assertIn("DONE answered=0 refused=1", out)
            # no id recoverable -> the answer is named after the file itself
            path = box.answered / "broken.query.json.answer.json"
            self.assertTrue(path.is_file())
            answer = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(answer["ok"])
            self.assertEqual(answer["error"], "query_malformed")
            self.assertIsNone(answer["data"])
            self.assertFalse((box.pending / "broken.query.json").exists())

    def test_range_crossing_eof_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Harness(tmp)
            box.add_query("q_trap_eof", "bytes",
                          {"offset": IMAGE_SIZE - 2, "length": 16})
            code, _ = box.run()
            self.assertEqual(code, 0)
            answer = box.answer("q_trap_eof")
            self.assertFalse(answer["ok"])
            self.assertEqual(answer["error"], "range_outside_image")
            self.assertIsNone(answer["data"])


class ConsoleAsciiTests(unittest.TestCase):
    """Thai lives in the JSON files (data); the console stays ASCII."""

    def test_thai_why_answers_fine_and_stdout_is_pure_ascii(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            box = Harness(tmp)
            box.add_query("q_thai_001", "bytes", {"offset": 16, "length": 8},
                          why=THAI_WHY)
            proc = subprocess.run(
                [sys.executable, str(TOOL),
                 "--image", str(box.image),
                 "--pending", str(box.pending),
                 "--answered", str(box.answered)],
                capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            stdout = proc.stdout.decode("ascii")  # must not raise
            self.assertIn("ANSWERED q_thai_001 kind=bytes ok=1", stdout)
            self.assertIn("DONE answered=1 refused=0", stdout)
            answer = box.answer("q_thai_001")
            self.assertTrue(answer["ok"])
            self.assertEqual(answer["data"]["hex"],
                             box.image_bytes[16:24].hex().upper())
            # the answer JSON is data, not console: the Thai must survive
            self.assertEqual(answer["query_verbatim"]["why"], THAI_WHY)


if __name__ == "__main__":
    unittest.main()
