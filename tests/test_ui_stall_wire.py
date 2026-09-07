"""Pure unit tests for ``ui_stall_wire.py`` -- ``StallOpenVital``
(``0x2A3E``) / ``StallStartVital`` (``0x30FE``) / ``StallOperateVital``
(``0x3DE4``) encode/decode.

Not wiring tests -- see ``ui_social_wire.py``'s module docstring. Every
class here is static-only (``PF_FIELD_VALIDATION.tsv`` says
``NOT_OBSERVED`` in both directions), so nothing below asserts a meaning,
a direction, or that any client ever saw one of these frames.

The byte-level expectations are written out literally rather than by
calling the encoder twice, so a change to the tag legend or the field
order fails here instead of agreeing with itself.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_stall_wire as sw  # noqa: E402


def _open_fields(**kw):
    base = dict(
        field1_u64=0x0102030405060708,
        field2_u16=0x1122,
        field3_wstring="stall",
        field4_u32=0xDEADBEEF,
        field5_u16=3,
        field6_u16=0,
    )
    base.update(kw)
    return sw.StallOpenFields(**base)


def _start_fields(**kw):
    base = dict(
        field1_u8=0x7F,
        field2_u16=0x2233,
        field3_wstring="a",
        field4_u16=9,
        field5_u16=0,
        members=(),
    )
    base.update(kw)
    return sw.StallStartFields(**base)


def _operate_fields(**kw):
    base = dict(
        field1_u8=2,
        field2_u64=0xFFFFFFFFFFFFFFFF,
        field3_wstring="",
        field4_u32=17,
        field5_u8=1,
        members=(),
    )
    base.update(kw)
    return sw.StallOperateFields(**base)


MEMBER_A = sw.StallMemberRecord(
    field1_u64=0x1122334455667788,
    field2_u32=0x00C0FFEE,
    field3_u16=0x0203,
    field4_u32=7,
)
MEMBER_B = sw.StallMemberRecord(
    field1_u64=1, field2_u32=2, field3_u16=3, field4_u32=4
)


class VitalIdTests(unittest.TestCase):
    """The three ids as spelled in
    ``pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`` lines 54,
    68 and 89 -- transcribed, not derived, so a typo is caught here."""

    def test_ids(self):
        self.assertEqual(sw.STALL_OPEN_VITAL_ID, 0x2A3E)
        self.assertEqual(sw.STALL_START_VITAL_ID, 0x30FE)
        self.assertEqual(sw.STALL_OPERATE_VITAL_ID, 0x3DE4)


class StallOpenWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = _open_fields()
        self.assertEqual(
            sw.decode_stall_open_payload(
                sw.encode_stall_open_payload(fields)
            ),
            fields,
        )

    def test_exact_bytes_and_field_order(self):
        payload = sw.encode_stall_open_payload(
            _open_fields(field3_wstring="ab")
        )
        expected = (
            b"\x32\x08\x07\x06\x05\x04\x03\x02\x01"  # 0x32 u64  @+0x18
            b"\x0f\x22\x11"                          # 0x0f u16  @+0x20
            b"\x48\x04\x00\x00\x00a\x00b\x00"        # 0x48 wstring @+0x24
            b"\x14\xef\xbe\xad\xde"                  # 0x14 u32  @+0x60
            b"\x0f\x03\x00"                          # 0x0f u16  STACK+0x18
            b"\x0f\x00\x00"                          # 0x0f u16  PHI(...)+0xC
        )
        self.assertEqual(payload, expected)

    def test_six_fields_exactly_five_tagged_plus_one_string(self):
        """RE-294's call census for ``0x0076A960`` counted 5 tagged writes
        and 1 string write. Anything this encoder emits beyond that would
        contradict the measurement the module is built on."""

        payload = sw.encode_stall_open_payload(_open_fields())
        tags = []
        offset = 0
        widths = {0x32: 8, 0x0F: 2, 0x14: 4}
        while offset < len(payload):
            tag = payload[offset]
            tags.append(tag)
            if tag == 0x48:
                length = int.from_bytes(
                    payload[offset + 1:offset + 5], "little"
                )
                offset += 5 + length
            else:
                offset += 1 + widths[tag]
        self.assertEqual(tags, [0x32, 0x0F, 0x48, 0x14, 0x0F, 0x0F])
        self.assertEqual(len([t for t in tags if t != 0x48]), 5)
        self.assertEqual(len([t for t in tags if t == 0x48]), 1)

    def test_truncated_payload_fails_closed(self):
        payload = sw.encode_stall_open_payload(_open_fields())
        for cut in range(1, len(payload)):
            with self.subTest(cut=cut):
                self.assertIsNone(sw.decode_stall_open_payload(payload[:cut]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        # COO-DECISION 20260904_1745 item 2 -- see test_ui_party_wire.py's
        # equivalent test for the full rationale.
        clean = sw.encode_stall_open_payload(_open_fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(sw.decode_stall_open_payload(clean + extra))

    def test_every_wrong_tag_byte_fails_closed(self):
        clean = bytearray(sw.encode_stall_open_payload(_open_fields()))
        tag_offsets = [0, 9, 12, 27, 32, 35]
        self.assertEqual(
            [clean[i] for i in tag_offsets], [0x32, 0x0F, 0x48, 0x14, 0x0F, 0x0F]
        )
        for i in tag_offsets:
            with self.subTest(tag_offset=i):
                broken = bytearray(clean)
                broken[i] ^= 0xFF
                self.assertIsNone(sw.decode_stall_open_payload(bytes(broken)))

    def test_empty_and_non_ascii_wstring(self):
        for text in ("", "a", "สตอล", "x" * 300):
            with self.subTest(text_len=len(text)):
                fields = _open_fields(field3_wstring=text)
                decoded = sw.decode_stall_open_payload(
                    sw.encode_stall_open_payload(fields)
                )
                self.assertEqual(decoded, fields)

    def test_empty_payload_fails_closed(self):
        self.assertIsNone(sw.decode_stall_open_payload(b""))


class StallStartWireTests(unittest.TestCase):
    def test_round_trip_without_members(self):
        fields = _start_fields()
        self.assertEqual(
            sw.decode_stall_start_payload(
                sw.encode_stall_start_payload(fields)
            ),
            fields,
        )

    def test_round_trip_with_members(self):
        for count in (1, 2, 5):
            with self.subTest(members=count):
                fields = _start_fields(
                    field5_u16=count, members=(MEMBER_A,) * count
                )
                self.assertEqual(
                    sw.decode_stall_start_payload(
                        sw.encode_stall_start_payload(fields)
                    ),
                    fields,
                )

    def test_exact_bytes_and_field_order(self):
        payload = sw.encode_stall_start_payload(
            _start_fields(field5_u16=1, members=(MEMBER_B,))
        )
        expected = (
            b"\x08\x7f"                              # 0x08 u8   @+0x14
            b"\x0f\x33\x22"                          # 0x0f u16  @+0x16
            b"\x48\x02\x00\x00\x00a\x00"             # 0x48 wstring @+0x18
            b"\x0f\x09\x00"                          # 0x0f u16  STACK+0x18
            b"\x0f\x01\x00"                          # 0x0f u16  PHI(...)+0xC
            b"\x32\x01\x00\x00\x00\x00\x00\x00\x00"  # member 0x32 elem+0x10
            b"\x14\x02\x00\x00\x00"                  # member 0x14 elem+0x18
            b"\x0f\x03\x00"                          # member 0x0f elem+0x1C
            b"\x19\x04\x00\x00\x00"                  # member 0x19 elem+0x20
        )
        self.assertEqual(payload, expected)

    def test_member_record_is_twenty_two_bytes(self):
        """(8+1) + (4+1) + (2+1) + (4+1) -- the four writes RE-294 decoded
        inside ``0x00766C00``, each with its tag byte."""

        one = sw.encode_stall_start_payload(
            _start_fields(members=(MEMBER_A,))
        )
        none = sw.encode_stall_start_payload(_start_fields())
        self.assertEqual(len(one) - len(none), 22)

    def test_a_truncated_member_record_fails_closed(self):
        payload = sw.encode_stall_start_payload(
            _start_fields(members=(MEMBER_A, MEMBER_B))
        )
        for cut in range(1, 22):
            with self.subTest(missing=cut):
                self.assertIsNone(
                    sw.decode_stall_start_payload(payload[:-cut])
                )

    def test_a_member_record_with_a_wrong_inner_tag_fails_closed(self):
        payload = bytearray(
            sw.encode_stall_start_payload(_start_fields(members=(MEMBER_B,)))
        )
        first_member = len(
            sw.encode_stall_start_payload(_start_fields())
        )
        for delta, expected_tag in ((0, 0x32), (9, 0x14), (14, 0x0F), (17, 0x19)):
            with self.subTest(inner_tag=expected_tag):
                self.assertEqual(payload[first_member + delta], expected_tag)
                broken = bytearray(payload)
                broken[first_member + delta] ^= 0xFF
                self.assertIsNone(
                    sw.decode_stall_start_payload(bytes(broken))
                )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = sw.encode_stall_start_payload(_start_fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(sw.decode_stall_start_payload(clean + extra))


class StallOperateWireTests(unittest.TestCase):
    def test_round_trip_without_members(self):
        fields = _operate_fields()
        self.assertEqual(
            sw.decode_stall_operate_payload(
                sw.encode_stall_operate_payload(fields)
            ),
            fields,
        )

    def test_round_trip_with_members(self):
        fields = _operate_fields(field5_u8=2, members=(MEMBER_A, MEMBER_B))
        self.assertEqual(
            sw.decode_stall_operate_payload(
                sw.encode_stall_operate_payload(fields)
            ),
            fields,
        )

    def test_exact_bytes_and_field_order(self):
        payload = sw.encode_stall_operate_payload(
            _operate_fields(field3_wstring="a", field2_u64=1)
        )
        expected = (
            b"\x08\x02"                              # 0x08 u8   @+0x14
            b"\x32\x01\x00\x00\x00\x00\x00\x00\x00"  # 0x32 u64  @+0x18
            b"\x48\x02\x00\x00\x00a\x00"             # 0x48 wstring @+0x24
            b"\x14\x11\x00\x00\x00"                  # 0x14 u32  @+0x20
            b"\x0b\x01"                              # 0x0b u8   STACK+0x14
        )
        self.assertEqual(payload, expected)

    def test_the_two_u8_tags_are_not_interchangeable(self):
        """field1 is tag ``0x08`` and field5 is tag ``0x0B``
        (``PF_SERIALIZER_FIELDS.tsv`` W1 vs W5). Swapping them must not
        decode."""

        payload = bytearray(
            sw.encode_stall_operate_payload(_operate_fields())
        )
        self.assertEqual(payload[0], 0x08)
        self.assertEqual(payload[-2], 0x0B)
        payload[0], payload[-2] = 0x0B, 0x08
        self.assertIsNone(sw.decode_stall_operate_payload(bytes(payload)))

    def test_truncated_payload_fails_closed(self):
        payload = sw.encode_stall_operate_payload(
            _operate_fields(members=(MEMBER_A,))
        )
        prefix_len = len(sw.encode_stall_operate_payload(_operate_fields()))
        for cut in range(1, len(payload)):
            if cut == prefix_len:
                # The one cut that is NOT a truncation: see
                # TruncationAtTheMemberBoundaryIsIndistinguishableTests.
                continue
            with self.subTest(cut=cut):
                self.assertIsNone(
                    sw.decode_stall_operate_payload(payload[:cut])
                )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = sw.encode_stall_operate_payload(_operate_fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    sw.decode_stall_operate_payload(clean + extra)
                )


class TruncationAtTheMemberBoundaryIsIndistinguishableTests(unittest.TestCase):
    """A member list may legitimately be empty, so a payload cut exactly at
    the end of the prefix decodes as a zero-member frame instead of
    failing.

    This is a real limit of a length-free repeated record, not an
    oversight, and it is pinned here so nobody reads the
    ``fails_closed`` tests above as covering it. It is also the one place
    where a proven count field would buy something: with nonclaim 2
    unproven, this decoder cannot tell "the sender sent no members" from
    "the members were lost in transit". Every cut that lands anywhere
    else -- inside the prefix, or partway through a record -- does fail
    closed, which the sibling tests cover byte by byte.
    """

    def test_a_cut_at_the_prefix_boundary_decodes_as_zero_members(self):
        """A first draft of this test compared two ENCODER outputs and
        never called a decoder -- pf-adversary killed it with a
        ``return None`` mutant that this class passed. It now asserts the
        decoded value, which is the behaviour the class is named for."""

        for encode, decode, empty, one in (
            (
                sw.encode_stall_start_payload,
                sw.decode_stall_start_payload,
                _start_fields(),
                _start_fields(members=(MEMBER_A,)),
            ),
            (
                sw.encode_stall_operate_payload,
                sw.decode_stall_operate_payload,
                _operate_fields(),
                _operate_fields(members=(MEMBER_A,)),
            ),
        ):
            with self.subTest(encoder=encode.__name__):
                prefix_len = len(encode(empty))
                cut = encode(one)[:prefix_len]
                self.assertEqual(cut, encode(empty))
                decoded = decode(cut)
                self.assertIsNotNone(decoded)
                self.assertEqual(decoded, empty)
                self.assertEqual(decoded.members, ())

    def test_any_cut_inside_a_member_record_fails_closed(self):
        payload = sw.encode_stall_operate_payload(
            _operate_fields(members=(MEMBER_A,))
        )
        prefix_len = len(sw.encode_stall_operate_payload(_operate_fields()))
        for cut in range(prefix_len + 1, len(payload)):
            with self.subTest(cut=cut):
                self.assertIsNone(
                    sw.decode_stall_operate_payload(payload[:cut])
                )


class MemberCountFieldIsAReportNotARuleTests(unittest.TestCase):
    """nonclaim 2: nothing in this module treats the trailing prefix field
    as the member count. These tests pin that it stays a report."""

    def test_a_disagreeing_count_still_round_trips_unchanged(self):
        fields = _start_fields(field5_u16=99, members=(MEMBER_A,))
        decoded = sw.decode_stall_start_payload(
            sw.encode_stall_start_payload(fields)
        )
        self.assertEqual(decoded, fields)
        self.assertEqual(decoded.field5_u16, 99)
        self.assertEqual(len(decoded.members), 1)

    def test_the_operate_class_round_trips_a_disagreement_too(self):
        """The operate class keeps the same round-trip guarantee, but its
        field5 is a PRESENCE flag (see member_count_field_agrees' own
        docstring), so the report deliberately does not accept it."""

        fields = _operate_fields(field5_u8=5, members=(MEMBER_B,))
        decoded = sw.decode_stall_operate_payload(
            sw.encode_stall_operate_payload(fields)
        )
        self.assertEqual(decoded, fields)
        with self.assertRaises(AttributeError):
            sw.member_count_field_agrees(decoded)

    def test_the_report_reads_the_right_field_per_class(self):
        self.assertTrue(
            sw.member_count_field_agrees(
                _start_fields(field5_u16=2, members=(MEMBER_A, MEMBER_B))
            )
        )
        self.assertFalse(
            sw.member_count_field_agrees(
                _start_fields(field5_u16=2, members=(MEMBER_A,))
            )
        )
        self.assertTrue(
            sw.member_count_field_agrees(
                _start_fields(field5_u16=0, members=())
            )
        )

    def test_decoding_never_consults_the_count_field(self):
        """Two payloads identical except for the count field decode to the
        same member list -- the loop is driven by the buffer, not by a
        field this lane has not proven."""

        low = sw.decode_stall_start_payload(
            sw.encode_stall_start_payload(
                _start_fields(field5_u16=0, members=(MEMBER_A, MEMBER_B))
            )
        )
        high = sw.decode_stall_start_payload(
            sw.encode_stall_start_payload(
                _start_fields(field5_u16=250, members=(MEMBER_A, MEMBER_B))
            )
        )
        self.assertEqual(low.members, high.members)
        self.assertEqual(len(low.members), 2)


class WhoGuaranteesThePayloadBoundaryTests(unittest.TestCase):
    """Round ``rgmulk``, answering the design question pf-adversary left
    open on round ``gkxzei``: nothing in a frame delimits the member list,
    so the CALLER's slice is the member count.

    The sibling class above pins the two cuts that were already known (a
    cut at the prefix boundary decodes as zero members; a cut inside a
    record fails closed). What was never measured is the cut a real
    dispatch caller is most likely to get wrong: a slice that is short or
    long by a WHOLE record. Those decode successfully and silently with
    the wrong member count, which is why ``_read_members`` now carries the
    precondition in writing. Measured here with real bytes so the claim in
    that docstring cannot drift away from the code.
    """

    def _record_len(self, encode, empty, one):
        return len(encode(one)) - len(encode(empty))

    def test_a_slice_short_by_one_whole_record_decodes_silently(self):
        for encode, decode, empty, three in (
            (
                sw.encode_stall_start_payload,
                sw.decode_stall_start_payload,
                _start_fields(members=()),
                _start_fields(
                    field5_u16=3, members=(MEMBER_A, MEMBER_B, MEMBER_A)
                ),
            ),
            (
                sw.encode_stall_operate_payload,
                sw.decode_stall_operate_payload,
                _operate_fields(members=()),
                _operate_fields(members=(MEMBER_A, MEMBER_B, MEMBER_A)),
            ),
        ):
            with self.subTest(encoder=encode.__name__):
                one = (
                    _start_fields(members=(MEMBER_A,))
                    if "start" in encode.__name__
                    else _operate_fields(members=(MEMBER_A,))
                )
                record_len = self._record_len(encode, empty, one)
                self.assertEqual(record_len, 22)
                payload = encode(three)
                decoded = decode(payload[:-record_len])
                self.assertIsNotNone(decoded)
                self.assertEqual(len(decoded.members), 2)

    def test_a_slice_long_by_one_whole_record_decodes_silently(self):
        three = _start_fields(
            field5_u16=3, members=(MEMBER_A, MEMBER_B, MEMBER_A)
        )
        four = _start_fields(
            field5_u16=3,
            members=(MEMBER_A, MEMBER_B, MEMBER_A, MEMBER_B),
        )
        payload = sw.encode_stall_start_payload(three)
        extra = sw.encode_stall_start_payload(four)[len(payload):]
        self.assertEqual(len(extra), 22)
        decoded = sw.decode_stall_start_payload(payload + extra)
        self.assertIsNotNone(decoded)
        self.assertEqual(len(decoded.members), 4)
        self.assertEqual(decoded.field5_u16, 3)

    def test_a_slice_wrong_by_anything_but_a_record_fails_closed(self):
        """The other half of the sentence: only record-aligned caller
        errors are silent. One byte either way is rejected, which is what
        makes the silent case worth naming separately."""

        payload = sw.encode_stall_start_payload(
            _start_fields(field5_u16=2, members=(MEMBER_A, MEMBER_B))
        )
        self.assertIsNone(sw.decode_stall_start_payload(payload[:-1]))
        self.assertIsNone(sw.decode_stall_start_payload(payload + b"\x00"))

    def test_the_only_in_frame_detector_covers_start_and_not_operate(self):
        """``member_count_field_agrees`` would catch both silent cases on
        ``StallStartVital`` -- it is a report a caller may consult, still
        not a rule (nonclaim 2). ``StallOperateVital`` has no detector at
        all: its field5 is a presence flag, so the report refuses it.
        """

        three = _start_fields(
            field5_u16=3, members=(MEMBER_A, MEMBER_B, MEMBER_A)
        )
        payload = sw.encode_stall_start_payload(three)
        record_len = 22
        self.assertTrue(sw.member_count_field_agrees(three))
        short = sw.decode_stall_start_payload(payload[:-record_len])
        self.assertFalse(sw.member_count_field_agrees(short))
        extra = payload[-record_len:]
        long_decoded = sw.decode_stall_start_payload(payload + extra)
        self.assertFalse(sw.member_count_field_agrees(long_decoded))
        operate = sw.decode_stall_operate_payload(
            sw.encode_stall_operate_payload(
                _operate_fields(members=(MEMBER_A, MEMBER_B))
            )
        )
        with self.assertRaises(AttributeError):
            sw.member_count_field_agrees(operate)

    def test_no_caller_outside_tests_hands_bytes_to_these_decoders(self):
        """The "nobody guarantees it today" half of the answer, measured
        rather than asserted in prose: if a dispatch caller ever lands,
        this test goes red and whoever wrote it must state which boundary
        it establishes (and update ``_read_members``' note).
        """

        root = Path(__file__).resolve().parents[1]
        hits = []
        for folder in ("src", "tools"):
            for path in sorted((root / folder).rglob("*.py")):
                if path.name == "ui_stall_wire.py":
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                for lineno, line in enumerate(text.splitlines(), 1):
                    if "decode_stall_" in line:
                        hits.append(
                            "%s:%d" % (path.relative_to(root), lineno)
                        )
        self.assertEqual(hits, [])


class MemberReaderIsWhatRejectsTrailingBytesTests(unittest.TestCase):
    """`require_exhausted` cannot fire in the two member-bearing decoders
    (the loop only exits when the buffer is exactly spent), so deleting it
    changes nothing -- pf-adversary proved that with two surviving
    mutants. The property those decoders actually rely on is that the
    member reader REJECTS a partial trailing record. That is what these
    tests pin, at the reader itself, so a future edit that bounds the loop
    by ``offset + 22 <= len(payload)`` (a mutant that survives the whole
    file today) goes red here."""

    def test_the_reader_raises_on_any_partial_trailing_record(self):
        record = sw._encode_member(MEMBER_A)
        self.assertEqual(len(record), 22)
        for keep in range(1, 22):
            with self.subTest(trailing_bytes=keep):
                with self.assertRaises(sw.wire.WireDecodeError):
                    sw._read_members(record + record[:keep], 0)

    def test_the_reader_consumes_whole_records_exactly(self):
        buf = sw._encode_member(MEMBER_A) + sw._encode_member(MEMBER_B)
        members, offset = sw._read_members(buf, 0)
        self.assertEqual(members, (MEMBER_A, MEMBER_B))
        self.assertEqual(offset, len(buf))


class U8MaskingTests(unittest.TestCase):
    """The two u8 encoders mask with ``& 0xFF``; nothing asserted what that
    does until pf-adversary showed the mask could be deleted with the file
    still green. Pinning current behaviour (truncate, do not raise) rather
    than changing it -- every sibling module in this lane masks the same
    way, so a change here is a house-wide decision, not this round's."""

    def test_an_over_wide_u8_truncates_rather_than_raising(self):
        payload = sw.encode_stall_start_payload(_start_fields(field1_u8=0x1FF))
        self.assertEqual(payload[:2], b"\x08\xff")
        self.assertEqual(
            sw.decode_stall_start_payload(payload).field1_u8, 0xFF
        )

    def test_the_operate_presence_byte_masks_the_same_way(self):
        payload = sw.encode_stall_operate_payload(_operate_fields(field5_u8=0x101))
        decoded = sw.decode_stall_operate_payload(payload)
        self.assertEqual(decoded.field5_u8, 0x01)


class ValueRangeTests(unittest.TestCase):
    def test_widths_are_masked_not_overflowed(self):
        wide = sw.encode_stall_open_payload(
            _open_fields(
                field1_u64=(1 << 64) - 1,
                field2_u16=0xFFFF,
                field4_u32=0xFFFFFFFF,
                field5_u16=0xFFFF,
                field6_u16=0xFFFF,
            )
        )
        decoded = sw.decode_stall_open_payload(wide)
        self.assertEqual(decoded.field1_u64, (1 << 64) - 1)
        self.assertEqual(decoded.field2_u16, 0xFFFF)
        self.assertEqual(decoded.field4_u32, 0xFFFFFFFF)

    def test_member_widths(self):
        record = sw.StallMemberRecord(
            field1_u64=(1 << 64) - 1,
            field2_u32=0xFFFFFFFF,
            field3_u16=0xFFFF,
            field4_u32=0xFFFFFFFF,
        )
        fields = _start_fields(members=(record,))
        self.assertEqual(
            sw.decode_stall_start_payload(
                sw.encode_stall_start_payload(fields)
            ),
            fields,
        )


if __name__ == "__main__":
    unittest.main()
