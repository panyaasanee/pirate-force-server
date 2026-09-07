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

import hashlib
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
# !! SOURCE, AND WHY IT IS QUOTED RATHER THAN RETYPED.  RE-292 tabulates
# FRAME 1 ONLY; its sentences about frames 2 and 3 are prose deltas, and
# frame 3's delta is ambiguous about which frame it is stated against.  The
# first version of this file read it as a delta from frame 1 and put `0b01`
# at byte 15 of frame 3 -- and because the same misreading produced BOTH the
# input and the expected table, they agreed with each other, no length check
# could notice (the byte does not change the 46 B total), and NOTHING in the
# repository could tell (pf-adversary round `uk16x4`, D1 then H2: restoring
# the wrong byte together with its wrong expected tuple left the suite
# green).
#
# The authority is the attended letter that spells all three frames out in
# full, not RE-292:
#
#   pf_bridge/notes_to_chief/20260907_0123_KA1A-R322B-RESULTS-GT281-screen-
#   PASS-GT279-execute-0x51E9-x3-bg0002-hostile-gap.md, lines 21/22/23.
#
# So the letter's own three hex lines are quoted here VERBATIM, spaces and
# all, and everything else in this file is derived from them:
#   * `_R322B_REGIONS` is the quoted text with the spaces removed;
#   * `_R322B_EXPECTED` is checked against a tag walker written from the
#     letter's own annotations, NOT from the shipped decoder, so a decoder
#     change cannot re-bless itself and a hand-edited table cannot agree
#     with itself either;
#   * `_R322B_LETTER_SHA256` pins the quoted text.
#
# NONCLAIM, and it is the ceiling of what this repository can check: the
# letter lives in `pf_bridge`, which is NOT beside this repository when the
# gate runs, so the hash pins the QUOTATION, not the letter.  Changing a
# fixture byte now takes three deliberate edits in three places that must be
# made to agree (line, hash, expected table) instead of one misreading that
# produced two agreeing halves.  It does not make a determined re-typing
# impossible; it makes an accident impossible.
_R322B_LETTER_LINES = (
    "0B 00 0B 01 14 01000000 14 00000000 0B 01 48 00000000 48 00000000",
    "0B 00 0B 01 14 01000000 14 00000000 0B 00 48 00000000 48 00000000",
    "0B 00 0B 01 14 00100000 14 00000000 0B 00 48 02000000 3000 48 00000000",
)

#: sha256 of the three lines above joined with "\n".  Pinned as a literal:
#: a test that recomputed the expected hash from the lines would pass for
#: every value of them.
_R322B_LETTER_SHA256 = (
    "95e6b3881cc680b3cfebe0bec47038c5f700387be6c2690147366772c9240eae"
)

_R322B_REGIONS = {
    n: bytes.fromhex(line.replace(" ", ""))
    for n, line in enumerate(_R322B_LETTER_LINES, start=1)
}

# What the R322B letter's bytes say each frame's class body decodes to.
# Written out as data, never derived from the shipped decoder, and
# cross-checked by `_walk_region_the_letters_way` below.
_R322B_EXPECTED = {
    1: (1, 1, 0, 1, "", ""),
    2: (1, 1, 0, 0, "", ""),
    3: (1, 0x1000, 0, 0, "0", ""),
}

# Tag bytes, spelled here rather than imported, because this walker's whole
# job is to be a SECOND opinion about the letter's bytes.  Importing the
# module under test would make it an echo.
_LETTER_TAG_U8 = 0x0B
_LETTER_TAG_U32 = 0x14
_LETTER_TAG_STR = 0x48


def _walk_region_the_letters_way(region: bytes) -> tuple:
    """Decode one quoted region using only what the LETTER says it is.

    The letter annotates frame 3 itself: `48 02000000 3000` is "a UTF-16
    string \"0\", 2 bytes long".  That plus the tag bytes is the entire
    grammar needed, so this function is written from the letter and not
    from `command_wire`, and it is deliberately strict -- every tag is
    asserted, so a fixture that drifted into a different shape raises here
    instead of quietly decoding to something.
    """

    def take_u8(buf, at, tag):
        if buf[at] != tag:
            raise AssertionError(f"tag 0x{buf[at]:02X} at {at}, want 0x{tag:02X}")
        return buf[at + 1], at + 2

    def take_u32(buf, at):
        if buf[at] != _LETTER_TAG_U32:
            raise AssertionError(f"tag 0x{buf[at]:02X} at {at}, want 0x14")
        return int.from_bytes(buf[at + 1 : at + 5], "little"), at + 5

    def take_str(buf, at):
        if buf[at] != _LETTER_TAG_STR:
            raise AssertionError(f"tag 0x{buf[at]:02X} at {at}, want 0x48")
        size = int.from_bytes(buf[at + 1 : at + 5], "little")
        at += 5
        return buf[at : at + size].decode("utf-16-le"), at + size

    # The envelope's own `0B <version>` pair, which parse_outer strips.
    _, at = take_u8(region, 0, _LETTER_TAG_U8)
    presence, at = take_u8(region, at, _LETTER_TAG_U8)
    field_0x10, at = take_u32(region, at)
    field_0x14, at = take_u32(region, at)
    field_0x18, at = take_u8(region, at, _LETTER_TAG_U8)
    string_0x1c, at = take_str(region, at)
    string_0x38, at = take_str(region, at)
    if at != len(region):
        raise AssertionError(f"{len(region) - at} byte(s) left over")
    return (presence, field_0x10, field_0x14, field_0x18, string_0x1c, string_0x38)


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


class TheFixtureCannotAgreeWithItsOwnMisreadingTests(unittest.TestCase):
    """pf-adversary round `uk16x4`, H2 -- the finding this class answers.

    D1 was a single wrong byte at frame 3 position 15.  What made it
    survive a whole round was not the byte: it was that ONE misreading of
    RE-292 produced BOTH the fixture input and the expected table, so the
    two agreed with each other.  The reviewer measured that restoring the
    wrong byte together with its wrong expected tuple left `28 passed, 47
    subtests passed` -- the fix was pinned by nothing, and frame 1 survived
    only by the accident of a second witness elsewhere in this file
    hardcoding `(1, 1, 1)`.

    Three checks make that accident unreachable, and each fails on its own:

    1. `test_the_quoted_letter_lines_are_pinned` -- the quoted text is
       hashed, so editing a fixture byte goes red before anything decodes.
    2. `test_the_expected_table_matches_an_independent_walk` -- the table is
       re-derived by `_walk_region_the_letters_way`, which is written from
       the letter's annotations and imports nothing from `command_wire`, so
       a hand-edited table cannot agree with itself and a decoder change
       cannot re-bless itself.
    3. `test_every_quoted_frame_is_covered` -- neither check can be dodged
       by adding a frame nothing looks at.

    NONCLAIM: this does not prove the letter says what is quoted.  The
    letter is in `pf_bridge`, which the gate does not have beside it.  It
    proves the quotation, the regions, and the expected table cannot drift
    apart, which is exactly the failure that happened.
    """

    def test_the_quoted_letter_lines_are_pinned(self):
        digest = hashlib.sha256(
            "\n".join(_R322B_LETTER_LINES).encode("ascii")
        ).hexdigest()
        self.assertEqual(
            digest,
            _R322B_LETTER_SHA256,
            "the quoted R322B lines changed.  If that was deliberate, go and"
            " read lines 21/22/23 of the attended letter again, then update"
            " the hash AND the expected table in the same commit.",
        )

    def test_the_expected_table_matches_an_independent_walk(self):
        for n, region in _R322B_REGIONS.items():
            with self.subTest(frame=n):
                self.assertEqual(
                    _walk_region_the_letters_way(region), _R322B_EXPECTED[n]
                )

    def test_the_walker_is_strict_about_every_tag_it_reads(self):
        """A walker that shrugged at a wrong tag would agree with any
        fixture, which is the defect it exists to prevent."""
        # Every TAG byte of frame 1's region: envelope version, presence,
        # the two u32 fields, the u8 field, and the two strings.
        for position in (0, 2, 4, 9, 14, 16, 21):
            with self.subTest(position=position):
                broken = bytearray(_R322B_REGIONS[1])
                broken[position] ^= 0xFF
                with self.assertRaises(AssertionError):
                    _walk_region_the_letters_way(bytes(broken))

    def test_the_walker_refuses_a_region_with_bytes_left_over(self):
        with self.assertRaises(AssertionError):
            _walk_region_the_letters_way(_R322B_REGIONS[1] + b"\x00")

    def test_frame_three_byte_fifteen_is_zero_and_that_is_the_whole_point(self):
        """The byte D1 was about, named so a grep for it lands here."""
        self.assertEqual(_R322B_REGIONS[3][15], 0x00)
        self.assertEqual(_R322B_EXPECTED[3][3], 0)

    def test_every_quoted_frame_is_covered(self):
        self.assertEqual(
            sorted(_R322B_REGIONS), sorted(_R322B_EXPECTED)
        )
        self.assertEqual(len(_R322B_REGIONS), len(_R322B_LETTER_LINES))


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

    #: The lengths ka1-A wrote down at the keyboard, one entry per frame.
    #: A dict rather than a list so that adding a fourth frame to
    #: `_R322B_LETTER_LINES` without recording its length is a KeyError, not
    #: a silently unchecked frame (pf-adversary round `uk16x4`, M4: the old
    #: `for n in (1, 2, 3)` loop made this file's headline nonclaim -- "the
    #: day a real multi-vital 0x51E9 is captured this sentence goes red" --
    #: impossible to redeem).
    ATTENDED_FRAME_LENGTHS = {1: 44, 2: 44, 3: 46}

    def test_the_three_regions_reproduce_the_attended_frame_lengths(self):
        """44/44/46 B -- the lengths ka1-A wrote down at the keyboard.

        What this pins, stated at the altitude it actually reaches: the
        letter's numbers are prefix (18 B) + region, so reproducing them is
        an INFERENCE FROM LENGTH that each frame carried exactly one vital
        (`vital_count == 1`).  Nobody counted a vital_count field on the
        wire; 18 + region is simply the only reading consistent with the 26
        bytes the letter itself spells out (the competing "framed size"
        convention of GT103AB was checked against those 26 bytes and does
        not fit).  [MEASURED lengths, INFERRED vital_count.]

        [PROPOSED, NOT MEASURED -- and it was labelled the other way round
        until pf-adversary M1] this is NOT "the check that notices" a region
        that did not come off a real frame.  H2 proved the opposite: a
        one-byte fixture error does not change any length, so no length
        check can see it.  What notices that is `_R322B_LETTER_SHA256` and
        `_walk_region_the_letters_way`, below.
        """
        self.assertEqual(
            {
                n: len(_outer_packet(self.legacy, region))
                for n, region in _R322B_REGIONS.items()
            },
            self.ATTENDED_FRAME_LENGTHS,
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
    """The day the boundary moves, this must fail -- not decode garbage.

    HOW FAR "LOUD" ACTUALLY REACHES, since the class name promises more than
    production delivers.  At the FUNCTION layer it is a raised
    `GmCommandWireError`, which is what these tests assert.  At the sink it
    is already quieter: `capture_raw_gm_command` swallows the exception into
    a `# decode: FAILED` COMMENT inside the capture file, so nothing fails
    and nobody is paged -- somebody has to read the file.  And that file
    lands under `capture/`, which `.gitignore` drops, so it never reaches a
    reviewer unless it is carried off the boot machine by hand.

    At R322B no capture file was written AT ALL (GT-279's negative result),
    which is the loudest reminder available that this class name describes a
    property of three functions, not a property of the system.
    """

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
