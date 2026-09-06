"""Regression pin on the payload slice the LIVE 0x51E9 capture chain is fed.

WHY THIS FILE EXISTS
====================
The chain is already wired and always on, measured on `origin/main` this
round (LANE-GM round `83wujr`):

    runtime.py:8589   if nested_id == GM_RUN_GM_COMMAND_VITAL_ID:
    runtime.py:8598       payload=bytes(parsed.nested_payload)
      -> lane_hooks/lane_gm_run_command.py  (production_allowed = True)
      -> gm/dispatch.handle_gm_run_command_vital
      -> gm/command_capture.capture_raw_gm_command

🔴 SELF-CORRECTION, recorded rather than quietly fixed: the first draft of
this file (and of the round file and a CORE-REQUEST letter that was written
and then deleted unsent) claimed the opposite -- "nothing calls the sink,
runtime has 0 hits".  That came from grepping runtime.py for the literals
`0x51E9` and `RunGMCommand`, which miss because the branch imports the
constant by name (`from .gm.dispatch import GM_RUN_GM_COMMAND_VITAL_ID`).
The house rule this broke is its own: a negative sentence needs a grep, and
the grep has to cover every spelling before the sentence is written.

What survives that correction is the gap that prompted the file, because it
is real either way: `gm/command_capture.py`'s docstring warns that a caller
handing the sink the whole frame instead of the payload slice "will not
crash, but every decode section will read FAILED forever", and nothing
tested that warning.  The live call site hands `parsed.nested_payload` --
the right slice, today.  If a future edit at that call site (or at either
hop between it and the sink) starts handing the whole frame instead, the
captures keep being written, they still look fine, and every one of them is
undecodable -- so the next attended boot where somebody presses a GM button
buys nothing, silently.  That is what this file now catches.

WHAT THIS FILE DOES NOT CLAIM
=============================
1. It does not pin the runtime-vital envelope's own layout.  This lane has
   not measured how many bytes precede the payload, and does not need to:
   the contract below is "any extra leading bytes break the decode", which
   is prefix-length-independent.  The prefix lengths used are illustrative.
2. It does not claim a FAILED decode section proves a wrong slice.  It pins
   the opposite -- see `FailedIsAmbiguousTests`: a wrong slice and a
   genuinely malformed client payload are indistinguishable from the capture
   file alone.  That ambiguity is a real limitation of the sink as it stands;
   this file pins it so a later round cannot assume it away.
3. It does not touch, test or assert anything about runtime.py's branch
   itself (chief's zone).  It tests the contract that branch must keep.
4. It does not claim any GM button works, or that a real client has ever
   sent 0x51E9.  Nobody has pressed one and measured.
"""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm.command_capture import capture_raw_gm_command

# Same construction as tests/test_gm_command_wire.py -- built from the RE-088
# pinned shape rather than imported from an encoder, because this direction
# is inbound (client->server) and has no encoder by design.
_FAILED_MARKER = "# decode: FAILED"


def _wstring(text: str) -> bytes:
    payload = text.encode("utf-16-le")
    return bytes((0x48,)) + struct.pack("<I", len(payload)) + payload


def _payload(
    field_0x10: int = 7,
    field_0x14: int = 9,
    field_0x18: int = 1,
    s1: str = "cmd",
    s2: str = "arg",
    presence: int = 1,
) -> bytes:
    """One well-formed GM_RunGMCommandVital PAYLOAD (no envelope)."""
    return (
        bytes([0x0B, presence])
        + bytes([0x14]) + struct.pack("<I", field_0x10)
        + bytes([0x14]) + struct.pack("<I", field_0x14)
        + bytes([0x0B, field_0x18])
        + _wstring(s1)
        + _wstring(s2)
    )


def _capture(raw: bytes) -> str:
    with TemporaryDirectory() as tmp:
        out = capture_raw_gm_command(raw, "gm_tester", capture_root=tmp)
        return out.read_text(encoding="utf-8")


def _hex_bytes(text: str) -> bytes:
    """Recover the captured bytes from the file's hex dump section.

    The dump is everything after the header block; each line carries
    whitespace-separated two-digit hex.  Header lines start with '#'.
    """
    out = bytearray()
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        for token in line.split():
            if len(token) == 2:
                try:
                    out.append(int(token, 16))
                except ValueError:
                    pass
    return bytes(out)


class CorrectSliceTests(unittest.TestCase):
    """The slice the live call site hands the sink today: payload only."""

    def test_payload_only_decodes_and_reports_its_fields(self):
        text = _capture(_payload())
        self.assertNotIn(_FAILED_MARKER, text)
        self.assertIn("# decode: presence=1", text)
        self.assertIn("field_0x10=7 field_0x14=9 field_0x18=1", text)
        self.assertIn('string_0x1c="cmd"', text)
        self.assertIn('string_0x38="arg"', text)

    def test_presence_zero_payload_is_not_a_splice_failure(self):
        """An empty-but-structurally-valid press must not look like a bug.

        RE-088: presence=0 means the serializer stops -- valid, empty.  If a
        reader treated this as a broken splice they would go hunting for a
        wiring bug that is not there.
        """
        text = _capture(bytes([0x0B, 0x00]))
        self.assertNotIn(_FAILED_MARKER, text)
        self.assertIn("# decode: presence=0", text)


class WrongSliceTests(unittest.TestCase):
    """The failure mode the sink's own docstring predicted and nothing tested.

    Not reachable from the call site as it stands today -- that is the point:
    this is the pin that keeps it unreachable.

    Prefix lengths here are illustrative of "an envelope was left on", NOT a
    measured envelope size -- see this module's nonclaim 1.
    """

    def test_any_leading_envelope_bytes_break_the_decode(self):
        good = _payload()
        for prefix_len in (1, 2, 3, 4, 6, 8):
            with self.subTest(prefix_len=prefix_len):
                text = _capture(bytes(prefix_len) + good)
                self.assertIn(_FAILED_MARKER, text)

    def test_a_realistic_id_and_version_prefix_breaks_the_decode(self):
        # Shaped like "vital id (u16le) + version byte" purely to make the
        # case concrete; the assertion does not depend on that being the
        # real envelope.
        prefix = struct.pack("<H", 0x51E9) + bytes([0x00])
        text = _capture(prefix + _payload())
        self.assertIn(_FAILED_MARKER, text)

    def test_the_wrong_slice_still_writes_every_byte_losslessly(self):
        """The sink's one hard guarantee must survive a wrong slice.

        If this ever regresses, a wrongly spliced capture stops being
        recoverable after the fact and the attended boot that produced it is
        wasted for good, not merely undecoded.
        """
        prefix = struct.pack("<H", 0x51E9) + bytes([0x00])
        raw = prefix + _payload()
        text = _capture(raw)
        self.assertIn(_FAILED_MARKER, text)
        self.assertEqual(_hex_bytes(text), raw)
        self.assertIn(f"length={len(raw)}", text)

    def test_the_correct_slice_is_also_written_losslessly(self):
        raw = _payload()
        text = _capture(raw)
        self.assertEqual(_hex_bytes(text), raw)
        self.assertIn(f"length={len(raw)}", text)


class FailedIsAmbiguousTests(unittest.TestCase):
    """Pin the limitation, do not let a later round assume it away.

    Both a wrong slice and a real client sending bytes that do not match the
    RE-088 pin produce the same `# decode: FAILED` line.  So the capture file
    ALONE cannot tell chief "your splice hands the wrong slice" apart from
    "the pin is wrong / the client sent something new" -- which is exactly
    the question GM-002 exists to answer.  Telling them apart needs a second
    signal (a known-good probe press, or an envelope-aware caller), and that
    is a known limitation of the sink, pinned here rather than assumed away.
    """

    def test_wrong_slice_and_malformed_payload_are_indistinguishable(self):
        wrong_slice = _capture(struct.pack("<H", 0x51E9) + bytes([0x00]) + _payload())
        # A payload whose first tag byte is not the pinned 0x0B: what a real
        # client would produce if the pin were wrong.
        malformed = _capture(bytes([0x99, 0x01]) + _payload()[2:])
        self.assertIn(_FAILED_MARKER, wrong_slice)
        self.assertIn(_FAILED_MARKER, malformed)

    def test_the_failed_line_is_machine_detectable(self):
        """Whatever tells them apart later, finding the failures is cheap.

        A reader can grep captures for this exact prefix; it must stay a
        stable, greppable literal rather than free prose.
        """
        text = _capture(bytes([0x99, 0x01]))
        failed_lines = [
            line for line in text.splitlines() if line.startswith(_FAILED_MARKER)
        ]
        self.assertEqual(len(failed_lines), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
