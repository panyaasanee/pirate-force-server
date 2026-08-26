"""GM-001: GM_UpdateGMStateVital body against the proven field layout.

Field layout and its span sha256 come from
pf_bridge/external/PF_SERIALIZER_FIELDS.tsv (GM_UpdateGMStateVital rows) --
see gm/state_wire.py's module docstring for the full citation.
"""
import struct
import unittest

from pirateforce_foundation.gm import state_wire


class _FakeLegacy:
    @staticmethod
    def u8tag(tag, value):
        return bytes([tag, value & 0xFF])

    @staticmethod
    def u32tag(tag, value):
        return bytes([tag]) + struct.pack("<I", value & 0xFFFFFFFF)


class TestGmStateWire(unittest.TestCase):
    def test_field_order_and_tags_match_the_proven_layout(self):
        body = state_wire.make_gm_state_body(_FakeLegacy, field_a=1, field_b=2, field_c=0x11223344)
        expected = (
            bytes([0x0B, 1])
            + bytes([0x0B, 2])
            + bytes([0x14]) + struct.pack("<I", 0x11223344)
        )
        self.assertEqual(body, expected)

    def test_field_a_out_of_byte_range_is_refused(self):
        with self.assertRaises(ValueError):
            state_wire.make_gm_state_body(_FakeLegacy, field_a=256, field_b=0, field_c=0)

    def test_field_b_out_of_byte_range_is_refused(self):
        with self.assertRaises(ValueError):
            state_wire.make_gm_state_body(_FakeLegacy, field_a=0, field_b=-1, field_c=0)

    def test_field_c_out_of_dword_range_is_refused(self):
        with self.assertRaises(ValueError):
            state_wire.make_gm_state_body(_FakeLegacy, field_a=0, field_b=0, field_c=1 << 32)

    def test_grant_and_revoke_are_the_documented_placeholder_values(self):
        self.assertEqual(
            state_wire.for_gm_grant(_FakeLegacy),
            state_wire.make_gm_state_body(_FakeLegacy, field_a=1, field_b=0, field_c=0),
        )
        self.assertEqual(
            state_wire.for_gm_revoke(_FakeLegacy),
            state_wire.make_gm_state_body(_FakeLegacy, field_a=0, field_b=0, field_c=0),
        )

    def test_grant_and_revoke_differ_only_in_field_a(self):
        grant = state_wire.for_gm_grant(_FakeLegacy)
        revoke = state_wire.for_gm_revoke(_FakeLegacy)
        self.assertNotEqual(grant, revoke)
        # first 2 bytes are field_a's own tag+value; everything after must match
        self.assertNotEqual(grant[:2], revoke[:2])
        self.assertEqual(grant[2:], revoke[2:])

    def test_span_sha256_is_pinned_to_the_proven_row(self):
        self.assertEqual(
            state_wire.SPAN_SHA256,
            "03b186737b43884c61c7e82dc9805f7ee161cce3ae3436f2c5d0a5db8033c661",
        )


if __name__ == "__main__":
    unittest.main()
