"""RE-292: where the runtime-vital ENVELOPE ends and 0x51E9's class body begins.

WHY THIS FILE EXISTS.  RE-292
(``pf_bridge/notes_to_chief/20260907_1315_RE-292-RESULT-first-0B-is-vital-
version-presence-is-the-second-pair.md``) measured that EVERY runtime vital
carries a one-byte ``vital_version`` under tag 0x0B, written by the common
envelope at VA 0x005F3993, between the u16 class id and the class
serializer's own first byte -- and that 0x51E9's class serializer then opens
with its OWN tag 0x0B byte, the presence flag.  Two 0x0B pairs in a row, and
only the layer you start counting at tells them apart.

That is a trap with a measured victim: reading the FIRST pair as presence
turns R322B's real 26-byte frame into "presence=0, 24 bytes left over" and
the command's fields are lost.  RE-292's BUILD_IMPACT item 1 asks for a
decoder that reads the version itself.  For THIS repository that would be
one field too many, because ``current/pf_login_game_server_v141.py``'s
``parse_outer`` already consumes ``nested_version = c.u8(0x0B)`` before it
slices ``nested_payload``.  This file pins that -- against RE-292's own
three real R322B frames, through v141's real parser -- so the claim is a
measurement that can go red, not a sentence in a docstring.

WHAT IS NOT CLAIMED.  Nothing here is client-observable evidence: no frame
left a server and no screen changed.  The three frames are the ATTENDED
LETTER's byte table re-entered by hand (RE-292 tabulates frame 1 only; see
the correction above ``_R322B_REGIONS``), not a capture file this repository
holds, and the outer packet around them is BUILT here from v141's own tag
writers rather than taken off a wire -- so these tests pin the BOUNDARY
between envelope and class body, which is all RE-292 answered, and claim
nothing about what any field means (RE-088's nonclaim still stands) or about
whether GT-279 passes.

AND THE NONCLAIM THAT COSTS THE MOST TO LEAVE OUT: the multi-vital shape
this file exercises has NEVER BEEN SEEN on a real 0x51E9 frame.  All three
frames ka1-A measured were 44/44/46 B = an 18 B prefix plus the region, i.e.
``vital_count == 1`` every time (pinned below, for free, so the day a real
multi-vital 0x51E9 is captured this sentence goes red rather than stale).
The multi-vital handling exists because v141's ``nested_payload`` slice
MAKES it reachable and the client is measured to bundle up to five vitals on
OTHER doors (R303, R313) -- not because this door has ever done it.
"""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.gm.command_capture import capture_raw_gm_command
from pirateforce_foundation.gm.command_wire import (
    GM_RUN_GM_COMMAND_VITAL_ID,
    VITAL_ENVELOPE_VERSION_TAG,
    GmCommandWireError,
    decode_gm_run_command_vital,
    decode_gm_run_command_vital_prefix,
)

# The three 0x51E9 frames the client put on the wire during attended boot
# R322B, as the NESTED-VITAL REGION: everything after the u16 class id, i.e.
# the envelope's `0B <version>` pair followed by the class serializer's bytes.
#
# !! SOURCE, CORRECTED.  RE-292 tabulates FRAME 1 ONLY; its sentences about
# frames 2 and 3 are prose deltas, and frame 3's delta is stated against
# FRAME 2, not frame 1.  Reading it as a delta from frame 1 is how the first
# version of this file put `0b01` at byte 15 of frame 3 -- and because the
# same misreading produced BOTH the input and the expected table below, they
# agreed with each other and no length check could notice (the byte does not
# change the 46 B total).  The authority for frames 2 and 3 is therefore the
# attended letter that spells all three out in full, not RE-292:
#
#   pf_bridge/notes_to_chief/20260907_0123_KA1A-R322B-RESULTS-GT281-screen-
#   PASS-GT279-execute-0x51E9-x3-bg0002-hostile-gap.md, line 23, which gives
#   frame 3 as
#       0B 00 0B 01 14 00100000 14 00000000 0B 00 48 02000000 3000 48 00000000
#                                           ^^^^^ zero, not one
_R322B_REGIONS = {
    1: bytes.fromhex(
        "0b00" "0b01" "1401000000" "1400000000" "0b01" "4800000000" "4800000000"
    ),
    2: bytes.fromhex(
        "0b00" "0b01" "1401000000" "1400000000" "0b00" "4800000000" "4800000000"
    ),
    3: bytes.fromhex(
        "0b00" "0b01" "1400100000" "1400000000" "0b00" "48020000003000" "4800000000"
    ),
}

# What the R322B letter's bytes say each frame's class body decodes to.
# Written out as data, not derived from the decoder, so a decoder change
# cannot quietly re-bless itself.
_R322B_EXPECTED = {
    1: (1, 1, 0, 1, "", ""),
    2: (1, 1, 0, 0, "", ""),
    3: (1, 0x1000, 0, 0, "0", ""),
}

#: id header (tag 0x12 + u16) + version pair (tag 0x0B + u8).  This is the
#: number the whole file is about: the class body starts here, not earlier.
_NESTED_HEADER_LEN = 5


def _outer_packet(legacy, region: bytes, vital_id: int = GM_RUN_GM_COMMAND_VITAL_ID):
    """One inbound pc carrying exactly one nested vital, built with v141's
    own tag writers so the fixture cannot drift away from the parser."""
    return (
        legacy.u16tag(0x12, 0x0BC2)          # outer id; any id, parse_outer
        + legacy.u32tag(0x14, 0)             # does not branch on it
        + legacy.u8tag(0x08, 0)              # outer version
        + legacy.u8tag(0x0B, 0x02)           # mask bit 0x02 = VitalData present
        + legacy.u16tag(0x12, 1)             # vital_count
        + legacy.u16tag(0x12, vital_id)
        + region
    )


class TheEnvelopeVersionIsStrippedBeforeThisLaneTests(unittest.TestCase):
    """RE-292 BUILD_IMPACT item 1, checked against the shipped parser."""

    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_parse_outer_consumes_the_version_pair(self):
        for n, region in _R322B_REGIONS.items():
            with self.subTest(frame=n):
                parsed = self.legacy.parse_outer(_outer_packet(self.legacy, region))
                self.assertEqual(parsed.nested_id, GM_RUN_GM_COMMAND_VITAL_ID)
                self.assertEqual(parsed.nested_version, 0)
                self.assertEqual(bytes(parsed.nested_payload), region[2:])

    def test_the_boundary_is_the_five_byte_nested_header(self):
        """The MECHANISM, not the spelling: whatever the bytes are, the class
        body must start exactly five bytes past the nested vital's offset."""
        for n, region in _R322B_REGIONS.items():
            with self.subTest(frame=n):
                pc = _outer_packet(self.legacy, region)
                parsed = self.legacy.parse_outer(pc)
                self.assertEqual(
                    bytes(parsed.nested_payload),
                    pc[parsed.nested_offset + _NESTED_HEADER_LEN:],
                )

    def test_both_pairs_really_do_carry_the_same_tag(self):
        """The reason the trap exists.  Pinned so no later round 'fixes' the
        ambiguity by sniffing the tag byte -- it cannot be told apart."""
        for n, region in _R322B_REGIONS.items():
            with self.subTest(frame=n):
                self.assertEqual(region[0], VITAL_ENVELOPE_VERSION_TAG)
                self.assertEqual(region[2], VITAL_ENVELOPE_VERSION_TAG)

    def test_the_three_regions_reproduce_the_attended_frame_lengths(self):
        """44/44/46 B -- the lengths ka1-A wrote down at the keyboard.

        Free to assert and it pins more than it looks.  The letter's numbers
        are prefix (18 B) + region, so reproducing them is also the
        statement that each of the three frames carried EXACTLY ONE vital:
        `vital_count == 1`.  If a later round ever swaps in a region that
        does not come off a real frame, this is the check that notices.
        """
        self.assertEqual(
            [len(_outer_packet(self.legacy, _R322B_REGIONS[n])) for n in (1, 2, 3)],
            [44, 44, 46],
        )

    def test_the_stripped_payload_decodes_to_re292_field_values(self):
        for n, region in _R322B_REGIONS.items():
            with self.subTest(frame=n):
                parsed = self.legacy.parse_outer(_outer_packet(self.legacy, region))
                body = decode_gm_run_command_vital(bytes(parsed.nested_payload))
                self.assertEqual(
                    (
                        body.presence,
                        body.field_0x10,
                        body.field_0x14,
                        body.field_0x18,
                        body.string_0x1c,
                        body.string_0x38,
                    ),
                    _R322B_EXPECTED[n],
                )


class AnUnstrippedEnvelopeIsLoudNeverSilentTests(unittest.TestCase):
    """The day the boundary moves, this must fail -- not decode garbage."""

    def test_the_whole_region_is_refused_by_the_strict_decoder(self):
        for n, region in _R322B_REGIONS.items():
            with self.subTest(frame=n):
                with self.assertRaises(GmCommandWireError) as caught:
                    decode_gm_run_command_vital(region)
                message = str(caught.exception)
                self.assertIn(f"{len(region) - 2} trailing byte(s) remain", message)
                self.assertIn("RE-292", message)

    def test_the_prefix_decoder_does_not_recover_an_unstripped_region(self):
        """`decode_..._prefix` exists for multi-vital frames.  It must not
        double as an envelope stripper: a zero presence is a zero presence."""
        for n, region in _R322B_REGIONS.items():
            with self.subTest(frame=n):
                body, consumed = decode_gm_run_command_vital_prefix(region)
                self.assertIsNone(body)
                self.assertEqual(consumed, 2)

    def test_no_region_ever_decodes_silently_into_a_wrong_body(self):
        """The property, over every prefix length an envelope could leave on.

        A refusal is recoverable; a clean decode of the wrong fields is not.
        """
        for n, region in _R322B_REGIONS.items():
            for extra in range(1, 6):
                with self.subTest(frame=n, extra=extra):
                    with self.assertRaises(GmCommandWireError):
                        decode_gm_run_command_vital(bytes(extra) + region[2:])

    def test_the_capture_header_names_the_cause_instead_of_just_failing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            out = capture_raw_gm_command(
                _R322B_REGIONS[1], "gm_tester", capture_root=tmp, now_ts=0
            )
            text = out.read_text(encoding="utf-8")
        self.assertIn("# decode: FAILED", text)
        self.assertIn("RE-292", text)


class AMultiVitalFrameKeepsItsCommandFieldsTests(unittest.TestCase):
    """v141 sets nested_payload to every byte after the FIRST vital's header,
    and the client is measured to bundle up to five vitals (R303/R313)."""

    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        # A second whole nested vital header appended to frame 1's class body.
        self.tail = self.legacy.u16tag(0x12, 0x0F01) + self.legacy.u8tag(0x0B, 0)
        self.body = _R322B_REGIONS[1][2:]

    def test_the_strict_decoder_still_refuses_it(self):
        with self.assertRaises(GmCommandWireError):
            decode_gm_run_command_vital(self.body + self.tail)

    def test_the_prefix_decoder_returns_the_command_and_the_byte_count(self):
        body, consumed = decode_gm_run_command_vital_prefix(self.body + self.tail)
        self.assertEqual(consumed, len(self.body))
        self.assertEqual(
            (body.presence, body.field_0x10, body.field_0x18), (1, 1, 1)
        )

    def test_the_capture_header_prints_the_fields_and_reports_the_leftover(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            out = capture_raw_gm_command(
                self.body + self.tail, "gm_tester", capture_root=tmp, now_ts=0
            )
            text = out.read_text(encoding="utf-8")
        self.assertNotIn("# decode: FAILED", text)
        self.assertIn("# decode: presence=1", text)
        self.assertIn("field_0x10=1 field_0x14=0 field_0x18=1", text)
        self.assertIn(f"# decode: TRAILING {len(self.tail)} byte(s)", text)

    def test_every_byte_is_still_on_disk(self):
        import tempfile

        raw = self.body + self.tail
        with tempfile.TemporaryDirectory() as tmp:
            out = capture_raw_gm_command(
                raw, "gm_tester", capture_root=tmp, now_ts=0
            )
            text = out.read_text(encoding="utf-8")
        recovered = bytearray()
        for line in text.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            for token in line.split():
                if len(token) == 2:
                    try:
                        recovered.append(int(token, 16))
                    except ValueError:
                        pass
        self.assertEqual(bytes(recovered), raw)
        self.assertIn(f"length={len(raw)}", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
