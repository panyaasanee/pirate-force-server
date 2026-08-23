"""GROUND-LOOT-001 (HYP-PF-032) -- the bit-0x08 frame lane, offline.

This file proves the pure half of the lane: the scenario file's role as a
permission token rather than a source of values, the named refusals of the
loader, the identity gate, and the exact composition of the TWO frames the
lane may emit -- one element per frame, count=1 each, the V43-proven-safe
single-record shape (a real client raised ErrorData=28317 on a combined
multi-record derived-mask collection; make_port_royal_npc_single_packets is
the shipped fix this lane mirrors).  Both pcs are rebuilt here INDEPENDENTLY
with ``struct`` from the GT-042 re-derived 0x5F85B0 wire table, never
through the module's own element helper.  It drives no dispatcher and opens
no database -- ``tests/test_ground_loot_dispatch.py`` drives the real
dispatcher.

NOT proven here, and not provable on any machine without a person at a
screen: whether the client RENDERS anything for a derived-bit-0x08 list.
Bit 0x08 = "ground loot" is UNPROVEN; the payload dword is NOT claimed to be
an item template id; drawing is not pickup.  No client has ever been shown a
bit-0x08 frame.  That is GT-045, attended, queued, not run.
"""
from __future__ import annotations

import hashlib
import struct
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ground_loot_hypothesis as glh  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "ground_loot_hypothesis_bit08_render.json"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest().upper()


class GroundLootScenarioTests(unittest.TestCase):
    """The scenario file is a permission token, never a source of values."""

    def setUp(self):
        self.body = SCENARIO_PATH.read_text(encoding="utf-8")
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text):
        path = Path(self.tmp.name) / "scenario.json"
        path.write_text(text, encoding="utf-8")
        return path

    def test_the_shipped_file_loads_and_yields_the_frozen_profile(self):
        loaded = glh.load_ground_loot_hypothesis_scenario(SCENARIO_PATH)
        self.assertIs(loaded, glh._BIT08_RENDER)
        self.assertEqual(loaded.hypothesis_id, "HYP-PF-032")
        self.assertEqual(
            loaded.scenario_id, "ground_loot_hypothesis_bit08_render",
        )
        self.assertEqual(len(loaded.elements), 2)

    def test_the_shipped_file_declares_the_v43_single_record_emission(self):
        self.assertIn(
            '"emission": '
            '"two_single_element_runtimeres_derived_bit08_frames_v43_shape"',
            self.body,
        )
        self.assertIn('"pc_size_each": 44', self.body)
        self.assertIn('"frame_size_each": 54', self.body)

    def test_a_tampered_element_key_is_refused_rather_than_obeyed(self):
        tampered = self.body.replace('"element_key": 1', '"element_key": 7')
        self.assertNotEqual(tampered, self.body)
        with self.assertRaises(ValueError) as caught:
            glh.load_ground_loot_hypothesis_scenario(self._write(tampered))
        self.assertIn("exceeds_allowlist", str(caught.exception))

    def test_an_extra_key_is_refused(self):
        extra = self.body.replace('{\n  "schema": 1,',
                                  '{\n  "extra": 1,\n  "schema": 1,')
        self.assertNotEqual(extra, self.body)
        with self.assertRaises(ValueError) as caught:
            glh.load_ground_loot_hypothesis_scenario(self._write(extra))
        self.assertIn("exceeds_allowlist", str(caught.exception))

    def test_a_missing_key_is_refused(self):
        missing = self.body.replace('  "schema": 1,\n', '')
        self.assertNotEqual(missing, self.body)
        with self.assertRaises(ValueError) as caught:
            glh.load_ground_loot_hypothesis_scenario(self._write(missing))
        self.assertIn("exceeds_allowlist", str(caught.exception))

    def test_an_int_where_a_float_is_expected_is_refused(self):
        tampered = self.body.replace('"x": -9209.95703125', '"x": -9209', 1)
        self.assertNotEqual(tampered, self.body)
        with self.assertRaises(ValueError) as caught:
            glh.load_ground_loot_hypothesis_scenario(self._write(tampered))
        self.assertIn("exceeds_allowlist", str(caught.exception))

    def test_a_non_json_file_is_refused_by_name(self):
        with self.assertRaises(ValueError) as caught:
            glh.load_ground_loot_hypothesis_scenario(self._write("{ not json"))
        self.assertIn("unreadable", str(caught.exception))

    def test_an_absent_file_is_refused_by_name(self):
        with self.assertRaises(ValueError) as caught:
            glh.load_ground_loot_hypothesis_scenario(
                Path(self.tmp.name) / "absent.json"
            )
        self.assertIn("unreadable", str(caught.exception))

    def test_an_unknown_id_is_refused_by_name(self):
        tampered = self.body.replace(
            '"id": "ground_loot_hypothesis_bit08_render"',
            '"id": "ground_loot_hypothesis_something_else"',
        )
        self.assertNotEqual(tampered, self.body)
        with self.assertRaises(ValueError) as caught:
            glh.load_ground_loot_hypothesis_scenario(self._write(tampered))
        self.assertIn("unknown_id", str(caught.exception))

    def test_a_value_equal_lookalike_profile_is_refused(self):
        lookalike = glh.GroundLootScenario(
            glh._BIT08_RENDER.scenario_id,
            glh._BIT08_RENDER.hypothesis_id,
            tuple(
                glh.GroundLootElement(
                    element.element_key, element.payload_dword,
                    element.x, element.y, element.z,
                )
                for element in glh._BIT08_RENDER.elements
            ),
        )
        self.assertEqual(lookalike, glh._BIT08_RENDER)
        with self.assertRaises(ValueError) as caught:
            glh.require_ground_loot_hypothesis_scenario(lookalike)
        self.assertIn("not_allowlisted", str(caught.exception))
        self.assertIs(
            glh.require_ground_loot_hypothesis_scenario(glh._BIT08_RENDER),
            glh._BIT08_RENDER,
        )


# The GT-042 re-derived element table, restated HERE so the composition test
# below shares no code with the module's _element_wire: key 1 near the V135
# spawn (+30 on X only), key 2 far (+800 on X only), both carrying the
# OUR-DESIGN payload dword 2600001 under element mask 0x12 (position+dword).
# Each element travels in its OWN frame, count=1 -- the V43 lesson.
EXPECTED_ELEMENTS = (
    (1, 2600001, -9209.95703125, -2830.045166015625, 223.29209899902344),
    (2, 2600001, -8439.95703125, -2830.045166015625, 223.29209899902344),
)
EXPECTED_PIN_PAIRS = (
    ("A3570BC9185BEF70ABB3810448F6E3F605437B2F1BFAB1DF474882AD3661EA03",
     "A9D4F13409DF636C40FEA7FE7DEA38DD542D09E140BB073FBDD367B5758A5AE0"),
    ("4B14A026763F53FFD65210C2F2BCC0122B096A6877455C84DAAED71366F07F3A",
     "B13942BBCC933B4E135BCD40FE0C3D39B4EF053C31892F1F8EC929F702223989"),
)
SNAPPY_MAGIC = 0x5F253EAC


def independent_pc(element) -> bytes:
    """One 44-byte single-element pc, from struct alone -- no module helper."""
    key, dword, x, y, z = element
    pc = bytearray()
    pc += b"\x12" + struct.pack("<H", 0x6E9D)   # msg id
    pc += b"\x14" + struct.pack("<I", 0)        # envelope u32
    pc += bytes([0x08, 4])                      # version 4
    pc += bytes([0x0B, 0])                      # inherited mask: none
    pc += bytes([0x0B, 0x08])                   # derived mask bit 0x08
    pc += b"\x12" + struct.pack("<H", 1)        # count: ONE element
    pc += b"\x14" + struct.pack("<I", key)      # +0x10 key
    pc += bytes([0x0B, 0x12])                   # +0x28 dirty mask
    pc += b"\x14" + struct.pack("<I", dword)    # +0x14 (bit 0x02)
    pc += b"\x2A" + struct.pack("<f", x)        # +0x1C (bit 0x10)
    pc += b"\x2A" + struct.pack("<f", y)        # +0x20
    pc += b"\x2A" + struct.pack("<f", z)        # +0x24
    return bytes(pc)


def independent_frame(pc: bytes) -> bytes:
    """Snappy raw-literal + <II> magic/len header, restated from struct."""
    length = len(pc)
    assert 0 < length <= 60 < 128  # varint 1 byte, short-literal tag
    comp = bytes([length]) + bytes([(length - 1) << 2]) + pc
    return struct.pack("<II", SNAPPY_MAGIC, len(comp)) + comp


class GroundLootCompositionTests(unittest.TestCase):
    """The composer against an independent rebuild of the re-derived wire."""

    def setUp(self):
        self.legacy = _legacy()
        self.scenario = glh.load_ground_loot_hypothesis_scenario(SCENARIO_PATH)

    def test_the_composed_pcs_equal_the_independent_struct_rebuild(self):
        frames = glh.make_ground_loot_frames(self.legacy, self.scenario)
        self.assertEqual(len(frames), 2)
        for (pc, frame), element in zip(frames, EXPECTED_ELEMENTS):
            with self.subTest(element_key=element[0]):
                self.assertEqual(pc, independent_pc(element))
                self.assertEqual(frame, independent_frame(independent_pc(
                    element)))

    def test_all_six_pins_hold_on_the_composed_bytes(self):
        frames = glh.make_ground_loot_frames(self.legacy, self.scenario)
        self.assertEqual(
            EXPECTED_PIN_PAIRS,
            (
                (glh.GROUND_LOOT_NEAR_PC_SHA256,
                 glh.GROUND_LOOT_NEAR_FRAME_SHA256),
                (glh.GROUND_LOOT_FAR_PC_SHA256,
                 glh.GROUND_LOOT_FAR_FRAME_SHA256),
            ),
        )
        for (pc, frame), (pc_sha, frame_sha) in zip(
                frames, EXPECTED_PIN_PAIRS):
            with self.subTest(pc_sha=pc_sha):
                self.assertEqual(len(pc), glh.GROUND_LOOT_PC_SIZE)
                self.assertEqual(len(pc), 44)
                self.assertEqual(_sha(pc), pc_sha)
                self.assertEqual(len(frame), glh.GROUND_LOOT_FRAME_SIZE)
                self.assertEqual(len(frame), 54)
                self.assertEqual(_sha(frame), frame_sha)
                self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_the_tag_bytes_and_field_order_match_the_rederived_table(self):
        frames = glh.make_ground_loot_frames(self.legacy, self.scenario)
        for (pc, _), (key, dword, x, y, z) in zip(frames, EXPECTED_ELEMENTS):
            with self.subTest(element_key=key):
                # Envelope: u16tag(0x12) id, u32tag(0x14) 0, u8tag(0x08)
                # version 4, u8tag(0x0B) inherited mask 0, u8tag(0x0B)
                # derived mask 0x08, u16tag(0x12) count 1 -- NEVER 2.
                self.assertEqual(pc[0], 0x12)
                self.assertEqual(struct.unpack_from("<H", pc, 1)[0], 0x6E9D)
                self.assertEqual(pc[3], 0x14)
                self.assertEqual(struct.unpack_from("<I", pc, 4)[0], 0)
                self.assertEqual(pc[8:10], bytes([0x08, 4]))
                self.assertEqual(pc[10:12], bytes([0x0B, 0]))
                self.assertEqual(pc[12:14], bytes([0x0B, 0x08]))
                self.assertEqual(pc[14], 0x12)
                self.assertEqual(struct.unpack_from("<H", pc, 15)[0], 1)
                # The one element: u32tag(0x14) key, u8tag(0x0B) mask 0x12,
                # u32tag(0x14) payload dword, then three f32tag (tag byte
                # 0x2A) x, y, z -- position LAST, in that order, nothing
                # else.
                at = 17
                self.assertEqual(pc[at], 0x14)
                self.assertEqual(struct.unpack_from("<I", pc, at + 1)[0], key)
                self.assertEqual(pc[at + 5:at + 7], bytes([0x0B, 0x12]))
                self.assertEqual(pc[at + 7], 0x14)
                self.assertEqual(
                    struct.unpack_from("<I", pc, at + 8)[0], dword,
                )
                for offset, value in ((12, x), (17, y), (22, z)):
                    self.assertEqual(pc[at + offset], 0x2A)
                    self.assertEqual(
                        struct.unpack_from("<f", pc, at + offset + 1)[0],
                        struct.unpack("<f", struct.pack("<f", value))[0],
                    )
                self.assertEqual(at + 27, len(pc))

    def test_a_moved_v135_placement_refuses_to_compose_by_name(self):
        class _MovedLegacy:
            V135_PLAYER_X = self.legacy.V135_PLAYER_X + 1.0
            V135_PLAYER_Y = self.legacy.V135_PLAYER_Y
            V135_PLAYER_Z = self.legacy.V135_PLAYER_Z

        with self.assertRaises(RuntimeError) as caught:
            glh.make_ground_loot_frames(_MovedLegacy(), self.scenario)
        self.assertIn("placement_drift", str(caught.exception))

    def test_the_composer_refuses_a_lookalike_before_composing(self):
        lookalike = glh.GroundLootScenario(
            glh._BIT08_RENDER.scenario_id,
            glh._BIT08_RENDER.hypothesis_id,
            glh._BIT08_RENDER.elements,
        )
        with self.assertRaises(ValueError) as caught:
            glh.make_ground_loot_frames(self.legacy, lookalike)
        self.assertIn("not_allowlisted", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
