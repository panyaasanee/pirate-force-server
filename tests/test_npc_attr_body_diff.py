"""LANE-B: the NPCAttr body walk names fields, or refuses.

The walk is the instrument the P-2 colour sweep reads its answer with, so
every refusal below is load-bearing: a walker that guesses a width silently
mis-names every field after the guess, and the attended tester would grade a
row against the wrong label.
"""
from __future__ import annotations

import pathlib
import struct
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import npc_attr_body_diff as bodydiff  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


class _BodyBuilder:
    """Bodies are built with the frozen encoders, never typed as hex here."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def _npc_body(self, **kwargs) -> bytes:
        params = dict(
            template_id=1, actor_identity=0x6E21, scene_id=1, scene_seq=0,
            visual_preset="P_MALE_002_000_SP1", current_hp=100, max_hp=100,
            movement_speed=0.0, basic_name="N-BASE",
        )
        params.update(kwargs)
        return self.legacy.make_npc_attr(
            params["template_id"], params["actor_identity"], params["scene_id"],
            params["scene_seq"], params["visual_preset"], params["current_hp"],
            params["max_hp"], movement_speed=params["movement_speed"],
            basic_name=params["basic_name"],
        )


class BodyWalkTests(_BodyBuilder, unittest.TestCase):
    def test_the_walk_names_every_field_the_frozen_encoder_wrote(self) -> None:
        fields = bodydiff.walk(self._npc_body())
        self.assertEqual(
            [f.key for f in fields],
            [
                "attr_head", "actor_identity", "basic_field_mask", "basic_name",
                "current_hp", "max_hp", "movement_speed", "scene_id",
                "scene_sequence", "npc_field_mask", "template_id",
                "visual_preset",
            ],
        )
        by = {f.key: f for f in fields}
        self.assertEqual(by["basic_name"].value, "N-BASE")
        self.assertEqual(by["current_hp"].value, 100)
        self.assertEqual(by["template_id"].value, 1)
        self.assertEqual(by["visual_preset"].value, "P_MALE_002_000_SP1")
        self.assertEqual(by["scene_id"].value, 1)

    def test_a_nameless_body_simply_has_no_name_field(self) -> None:
        keys = [f.key for f in bodydiff.walk(self._npc_body(basic_name=""))]
        self.assertNotIn("basic_name", keys)
        self.assertIn("current_hp", keys)

    def test_the_walk_consumes_the_whole_body_and_offsets_point_at_the_value(self) -> None:
        body = self._npc_body()
        for field in bodydiff.walk(body):
            self.assertEqual(
                body[field.body_offset:field.body_offset + len(field.raw)],
                field.raw,
                f"{field.key} offset does not point at its own bytes",
            )
        last = bodydiff.walk(body)[-1]
        self.assertEqual(last.body_offset + len(last.raw), len(body))

    def test_trailing_bytes_are_refused_not_ignored(self) -> None:
        with self.assertRaises(bodydiff.NpcAttrBodyWalkError):
            bodydiff.walk(self._npc_body() + b"\x0b\x01")

    def test_a_truncated_body_is_refused(self) -> None:
        with self.assertRaises(bodydiff.NpcAttrBodyWalkError):
            bodydiff.walk(self._npc_body()[:-4])

    def test_a_mask_bit_with_no_known_tag_stops_the_walk(self) -> None:
        # BasicAttr 0x0010/0x0020 are RE-117's MP pair: named, never shipped,
        # no tag anywhere in this codebase.  Walking past them would guess.
        body = bytearray(self._npc_body())
        # attr_head (tag+u8) + identity (tag+qword) + the mask tag byte.
        mask_at = 1 + 1 + 1 + 8 + 1
        mask = int.from_bytes(body[mask_at:mask_at + 2], "little")
        body[mask_at:mask_at + 2] = int(mask | 0x0010).to_bytes(2, "little")
        with self.assertRaises(bodydiff.NpcAttrBodyWalkError) as caught:
            bodydiff.walk(bytes(body))
        self.assertIn("0x0010", str(caught.exception))

    def test_an_unknown_mask_bit_stops_the_walk(self) -> None:
        body = bytearray(self._npc_body())
        mask_at = 1 + 1 + 1 + 8 + 1
        mask = int.from_bytes(body[mask_at:mask_at + 2], "little")
        body[mask_at:mask_at + 2] = int(mask | 0x8000).to_bytes(2, "little")
        with self.assertRaises(bodydiff.NpcAttrBodyWalkError):
            bodydiff.walk(bytes(body))

    def test_a_field_carrying_the_wrong_tag_is_refused(self) -> None:
        body = bytearray(self._npc_body())
        body[0] = 0x2A  # attr_head should be tag 0x0B
        with self.assertRaises(bodydiff.NpcAttrBodyWalkError):
            bodydiff.walk(bytes(body))

    def test_the_walk_takes_bytes_only(self) -> None:
        with self.assertRaises(bodydiff.NpcAttrBodyWalkError):
            bodydiff.walk(bytearray(self._npc_body()))


class BodyDiffTests(_BodyBuilder, unittest.TestCase):
    def test_a_body_does_not_differ_from_itself(self) -> None:
        self.assertEqual(bodydiff.diff(self._npc_body(), self._npc_body()), ())

    def test_one_changed_value_is_reported_as_one_field(self) -> None:
        deltas = bodydiff.diff(self._npc_body(), self._npc_body(template_id=916))
        self.assertEqual([d.spec.key for d in deltas], ["template_id"])
        self.assertEqual((deltas[0].left, deltas[0].right), (1, 916))
        self.assertTrue(deltas[0].present_in_both)
        self.assertEqual(deltas[0].spec.offset, "NPCAttr+0x78")

    def test_a_field_present_on_one_side_only_is_one_sided(self) -> None:
        deltas = bodydiff.diff(self._npc_body(), self._npc_body(basic_name=""))
        self.assertEqual(
            [(d.spec.key, d.present_in_both) for d in deltas],
            [("basic_field_mask", True), ("basic_name", False)],
        )
        self.assertIsNone(deltas[1].right)

    def test_a_float_field_compares_by_bytes_not_by_repr(self) -> None:
        deltas = bodydiff.diff(
            self._npc_body(movement_speed=0.0), self._npc_body(movement_speed=150.0),
        )
        self.assertEqual([d.spec.key for d in deltas], ["movement_speed"])
        self.assertAlmostEqual(deltas[0].right, 150.0, places=3)
        self.assertEqual(struct.pack("<f", 150.0), b"\x00\x00\x16\x43")

    def test_deltas_come_back_in_emission_order(self) -> None:
        deltas = bodydiff.diff(
            self._npc_body(),
            self._npc_body(template_id=916, current_hp=7, basic_name="X"),
        )
        self.assertEqual(
            [d.spec.key for d in deltas],
            ["basic_name", "current_hp", "template_id"],
        )

    def test_the_console_lines_are_ascii_and_carry_the_offset(self) -> None:
        deltas = bodydiff.diff(self._npc_body(), self._npc_body(template_id=916))
        lines = bodydiff.format_diff_lines("N-BASE", "M-BASE", deltas)
        for line in lines:
            line.encode("ascii")
        self.assertIn("fields=1", lines[0])
        self.assertIn("NPCAttr+0x78", lines[1])


class FieldSpecTableTests(unittest.TestCase):
    def test_every_spec_key_is_unique(self) -> None:
        specs = (
            bodydiff.BASIC_ALWAYS + bodydiff.BASIC_BIT_FIELDS
            + (bodydiff.NPC_ALWAYS,) + bodydiff.NPC_BIT_FIELDS
        )
        keys = [s.key for s in specs]
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_bit_field_declares_exactly_one_bit(self) -> None:
        for spec in bodydiff.BASIC_BIT_FIELDS + bodydiff.NPC_BIT_FIELDS:
            self.assertEqual(
                bin(spec.mask_bit).count("1"), 1, f"{spec.key} is not one bit",
            )

    def test_every_spec_names_its_source_and_a_tag_the_walker_knows(self) -> None:
        specs = (
            bodydiff.BASIC_ALWAYS + bodydiff.BASIC_BIT_FIELDS
            + (bodydiff.NPC_ALWAYS,) + bodydiff.NPC_BIT_FIELDS
        )
        for spec in specs:
            self.assertTrue(spec.source.strip(), f"{spec.key} cites nothing")
            self.assertTrue(
                spec.tag in bodydiff.TAG_WIDTHS
                or spec.tag in bodydiff.TAG_LENGTH_PREFIXED,
                f"{spec.key} uses a tag the walker cannot read",
            )

    def test_an_uncited_offset_says_so_rather_than_inventing_a_number(self) -> None:
        by_key = {
            s.key: s
            for s in bodydiff.BASIC_ALWAYS + bodydiff.BASIC_BIT_FIELDS
        }
        # The codex has no row for the level bit; the module must not print a
        # hex offset for it as though it did.
        self.assertEqual(by_key["level"].offset, bodydiff.UNCITED)
        self.assertIn("no codex row", by_key["level"].source)
        self.assertEqual(by_key["faction"].offset, "BasicAttr+0x68")


if __name__ == "__main__":
    unittest.main()
