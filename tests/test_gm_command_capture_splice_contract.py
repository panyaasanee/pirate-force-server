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


def _decode_lines(text: str) -> list[str]:
    """Just the `# decode:` block, so two captures can be compared by what
    the header SAYS rather than by their timestamps and hex dumps."""
    return [line for line in text.splitlines() if line.startswith("# decode:")]


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


class TheTailDirectionIsAlsoPinnedTests(unittest.TestCase):
    """The other half of the contract: bytes left over AFTER the body.

    Every case in `WrongSliceTests` puts its extra bytes at the FRONT, which
    is the direction a wrong splice at the call site produces.  When
    `decode_gm_run_command_vital_prefix` arrived (LANE-GM round `m133mu`, so
    a multi-vital frame stops costing the reader the command's fields), the
    OTHER direction quietly lost its `# decode: FAILED` line: any leftover at
    all printed the fields and called the frame multi-vital, a cause the sink
    cannot see.  A single stray `00` and a sixth field the RE-088 pin does
    not know both read as "multi-vital", byte for byte the same sentence.

    A nested vital opens with a FIVE-BYTE header -- `u16(tag 0x12)` class id
    then `u8(tag 0x0B)` version (RE-292) -- and checking those five bytes
    needs no body-length table, so it costs this sink neither a `vital_walk`
    import nor a `legacy` handle.  That is the rule
    `gm/chat_frame_tail.py:215` already ships, and the rule these tests pin.

    SELF-CORRECTION, recorded rather than quietly fixed (pf-adversary round
    `uk16x4`, H1/M2): the first version of this class checked byte 0 alone
    and this docstring called it "the one thing the sink CAN check".  Both
    were wrong.  v141's `parse_outer` (`:2902`) opens an OUTER packet with
    `outer_id = c.u16(0x12)`, so a second whole packet appended at the tail
    -- the likeliest splice bug there is -- passed the one-byte guard and was
    reported as a multi-vital frame with the greppable FAILED marker
    swallowed: D2's exact defect, re-entering through a different byte.  And
    the "one thing the sink CAN check" sentence was written without grepping
    this lane's own directory, where the stronger rule was already merged.

    `TheOneByteGuardIsNotEnoughTests` below pins every case that separates
    the two rules, so no future edit can quietly walk back to byte 0.
    """

    def test_a_single_stray_byte_at_the_tail_is_not_called_multi_vital(self):
        text = _capture(_payload() + bytes(1))
        self.assertIn(_FAILED_MARKER, text)
        self.assertNotIn("multi-vital frame", text)
        self.assertIn("TRAILING 1 byte(s)", text)
        self.assertIn("opening with tag 0x00", text)

    def test_an_unknown_sixth_field_at_the_tail_is_not_called_multi_vital(self):
        """What a real client sending one more field than RE-088 pinned looks
        like.  Before the guard this was indistinguishable, byte for byte,
        from the stray-byte case above and from a genuine second vital."""
        sixth = bytes([0x14]) + struct.pack("<I", 5)
        text = _capture(_payload() + sixth)
        self.assertIn(_FAILED_MARKER, text)
        self.assertNotIn("multi-vital frame", text)
        self.assertIn(f"TRAILING {len(sixth)} byte(s)", text)
        self.assertIn("opening with tag 0x14", text)

    def test_the_two_tail_causes_no_longer_print_the_same_line(self):
        stray = _capture(_payload() + bytes(1))
        sixth = _capture(_payload() + bytes([0x14]) + struct.pack("<I", 5))
        self.assertNotEqual(_decode_lines(stray), _decode_lines(sixth))

    def test_a_real_nested_vital_at_the_tail_is_not_a_failure(self):
        """The case the prefix decoder was written for must stay clean, or
        the guard has just re-broken what `m133mu` fixed."""
        tail = bytes([0x12]) + struct.pack("<H", 0x0F01) + bytes([0x0B, 0x00])
        text = _capture(_payload() + tail)
        self.assertNotIn(_FAILED_MARKER, text)
        self.assertIn("multi-vital frame", text)
        self.assertIn(f"TRAILING {len(tail)} byte(s)", text)
        self.assertIn("field_0x10=7 field_0x14=9 field_0x18=1", text)

    def test_the_fields_survive_every_tail_shape(self):
        """Whatever the tail is, the reader keeps what did decode -- that is
        the whole point of the prefix decoder and the guard must not undo
        it."""
        for label, tail in (
            ("stray", bytes(1)),
            ("sixth-field", bytes([0x14]) + struct.pack("<I", 5)),
            ("nested-vital", bytes([0x12]) + struct.pack("<H", 0x0F01)),
        ):
            with self.subTest(tail=label):
                text = _capture(_payload() + tail)
                self.assertIn("field_0x10=7 field_0x14=9 field_0x18=1", text)
                self.assertIn('string_0x1c="cmd"', text)

    def test_the_marker_stays_countable_on_a_tail_failure(self):
        """`FailedIsAmbiguousTests` below greps for exactly one marker line.
        A tail failure prints body lines too; it must still be exactly one."""
        for label, tail in (
            ("stray", bytes(1)),
            ("sixth-field", bytes([0x14]) + struct.pack("<I", 5)),
        ):
            with self.subTest(tail=label):
                text = _capture(_payload() + tail)
                lines = [
                    line
                    for line in text.splitlines()
                    if line.startswith(_FAILED_MARKER)
                ]
                self.assertEqual(len(lines), 1)

    def test_every_byte_is_still_written_whatever_the_tail(self):
        for label, tail in (
            ("stray", bytes(1)),
            ("sixth-field", bytes([0x14]) + struct.pack("<I", 5)),
            ("nested-vital", bytes([0x12]) + struct.pack("<H", 0x0F01)),
        ):
            with self.subTest(tail=label):
                raw = _payload() + tail
                text = _capture(raw)
                self.assertEqual(_hex_bytes(text), raw)
                self.assertIn(f"length={len(raw)}", text)


class TheOneByteGuardIsNotEnoughTests(unittest.TestCase):
    """Every input that separates `tail[0] == 0x12` from the five-byte rule.

    Each row here died under the one-byte guard that shipped in round
    `uk16x4` and lives under the header rule, or is the control that must
    keep working.  They exist to kill the mutants pf-adversary measured as
    SURVIVING the previous fixture set (M5): `0x12 in tail` at any position,
    `tail[0] & 0x12 == 0x12`, a length bound of 3 instead of 5, and the
    header rule itself weakened back to one byte.

    NONCLAIM, and it is the honest ceiling of this sink: the header rule is
    NECESSARY, NOT SUFFICIENT.  A second packet whose byte 3 happened to be
    0x0B would still pass it.  That is why the line the sink prints says
    "CONSISTENT WITH", and `test_the_passing_line_never_asserts_a_cause`
    below goes red the day somebody upgrades that wording.
    """

    #: The head of a second whole v141 packet: `u16tag(0x12, 0x0BC2)` then
    #: `u32tag(0x14, 0)` ... -- byte 0 is 0x12 and byte 3 is 0x14.  This is
    #: the tail splice H1 was about, built the same way
    #: `test_gm_run_command_envelope_version_boundary._outer_packet` builds
    #: one, so it cannot drift away from the parser it imitates.
    SECOND_PACKET_HEAD = bytes.fromhex("12c20b1400000000" "0800" "0b02" "1201")

    #: A real nested vital header: id 0x0F01, version 0.
    REAL_NESTED = bytes([0x12]) + struct.pack("<H", 0x0F01) + bytes([0x0B, 0x00])

    def _refused(self, label, tail):
        text = _capture(_payload() + tail)
        self.assertIn(_FAILED_MARKER, text, label)
        self.assertNotIn("multi-vital frame", text, label)
        self.assertIn(f"TRAILING {len(tail)} byte(s)", text, label)
        return text

    def test_the_head_of_a_second_packet_is_not_called_multi_vital(self):
        """H1 itself.  Under the one-byte guard this printed a multi-vital
        claim and NO failure marker."""
        self._refused("second-packet-head", self.SECOND_PACKET_HEAD)

    def test_a_tail_too_short_to_be_a_header_is_not_called_multi_vital(self):
        """A nested header is five bytes, so one, three and four cannot be
        one.  Kills a length bound of 3 as well as no bound at all."""
        for length in (1, 2, 3, 4):
            with self.subTest(length=length):
                self._refused(f"short-{length}", self.REAL_NESTED[:length])

    def test_a_five_byte_header_is_the_smallest_accepted_tail(self):
        text = _capture(_payload() + self.REAL_NESTED)
        self.assertNotIn(_FAILED_MARKER, text)
        self.assertIn("multi-vital frame", text)

    def test_a_nested_vital_carrying_a_body_is_still_accepted(self):
        """The fixture set used to be a monoculture of exactly-five-byte
        tails (M5).  A real second vital carries a body after its header."""
        tail = self.REAL_NESTED + bytes.fromhex("1407000000")
        text = _capture(_payload() + tail)
        self.assertNotIn(_FAILED_MARKER, text)
        self.assertIn("multi-vital frame", text)
        self.assertIn(f"TRAILING {len(tail)} byte(s)", text)

    def test_the_id_tag_must_be_at_byte_zero_not_merely_present(self):
        """Kills `0x12 in tail`."""
        self._refused(
            "tag-not-first", bytes([0x99, 0x12, 0x0F, 0x0B, 0x00])
        )

    def test_a_byte_that_merely_contains_the_tag_bits_is_refused(self):
        """Kills `tail[0] & 0x12 == 0x12`.  0x13, 0x1A, 0x32 and 0x92 all
        satisfy that mask; none of them is the tag."""
        for first in (0x13, 0x1A, 0x32, 0x92):
            with self.subTest(first=hex(first)):
                tail = bytes([first]) + self.REAL_NESTED[1:]
                text = self._refused(f"masked-{first:#04x}", tail)
                self.assertIn(f"opening with tag 0x{first:02X}", text)

    def test_the_version_tag_at_byte_three_is_load_bearing(self):
        """Kills dropping the `tail[3] == 0x0B` half of the rule.  0x14 is
        what a real second packet has there; the rest are neighbours."""
        for third in (0x14, 0x08, 0x0A, 0x0C, 0x12):
            with self.subTest(third=hex(third)):
                tail = bytearray(self.REAL_NESTED)
                tail[3] = third
                self._refused(f"byte3-{third:#04x}", bytes(tail))

    def test_the_passing_line_never_asserts_a_cause(self):
        """The wording is the claim.  A header check cannot prove a cause,
        so the line must hedge and must name its own limit."""
        text = _capture(_payload() + self.REAL_NESTED)
        self.assertIn("CONSISTENT WITH a multi-vital frame", text)
        self.assertIn("Necessary, not sufficient", text)
        self.assertNotIn("-- the shape of a", text)

    def test_the_refusal_line_still_carries_the_decoder_message(self):
        """Kills dropping `-- {exc}` from the FAILED line (M5): without it
        the marker is present but says nothing a reader can act on."""
        text = self._refused("second-packet-head", self.SECOND_PACKET_HEAD)
        self.assertIn("FAILED against RE-088 pin -- ", text)
        self.assertNotIn("FAILED against RE-088 pin\n", text)


class APresenceZeroFirstVitalIsNotAnUnstrippedEnvelopeTests(unittest.TestCase):
    """pf-adversary round `uk16x4`, M3.

    A multi-vital frame whose FIRST vital is empty (presence=0) used to land
    in the arm that accuses the caller of handing over an un-stripped
    runtime-vital envelope -- the same "assert a cause the sink cannot see"
    defect as D2 and H1, surviving on the other side of the branch.  The two
    shapes are in fact distinguishable without any body-length table: an
    un-stripped envelope's leftover opens `0x0B <version>`, which fails the
    nested header rule, while a real second vital opens `0x12`.
    """

    REAL_NESTED = bytes([0x12]) + struct.pack("<H", 0x0F01) + bytes([0x0B, 0x00])

    def test_an_empty_first_vital_with_a_second_vital_is_not_a_failure(self):
        text = _capture(bytes([0x0B, 0x00]) + self.REAL_NESTED)
        self.assertNotIn(_FAILED_MARKER, text)
        self.assertIn("multi-vital frame", text)
        self.assertIn("presence=0 for THIS vital", text)

    def test_an_unstripped_envelope_still_names_that_cause(self):
        """The control: the accusation is correct for the shape it was
        written for, and must not have been thrown away with M3."""
        text = _capture(
            bytes.fromhex(
                "0b00" "0b01" "1401000000" "1400000000" "0b01"
                "4800000000" "4800000000"
            )
        )
        self.assertIn(_FAILED_MARKER, text)
        self.assertIn("un-stripped runtime-vital envelope", text)
        self.assertNotIn("multi-vital frame", text)

    def test_no_field_is_claimed_for_a_vital_that_had_none(self):
        text = _capture(bytes([0x0B, 0x00]) + bytes([0x14, 0x01]))
        self.assertIn(_FAILED_MARKER, text)
        self.assertIn("No field decoded for this vital", text)
        self.assertNotIn("The fields above", text)


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
