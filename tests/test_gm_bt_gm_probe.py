"""RE-164: BT_GM click experiment fork -- frame construction/serialization only.

These tests verify byte-level construction of the probe's wire variants.
They NEVER claim, and must never be extended to claim, that GMUI_BASIC opens
-- that is a client-observable fact only an attended click test can produce
(see pf_bridge GAME_TEST_QUEUE.md's paired GT entry). See
gm/bt_gm_probe.py's module docstring for the full nonclaim.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.gm.state_wire import (
    GM_UPDATE_GM_STATE_VITAL_ID,
    make_gm_update_state_frame,
    make_gm_update_state_payload,
)
from pirateforce_foundation.gm.bt_gm_probe import (
    CONNECTION_CONTEXT_SUSPECT,
    CURRENT_UI_OBJECT_KEY_SUSPECT,
    GM_PLUGIN_MODEL_KEY_SUSPECT,
    HYPOTHESIS_LABEL,
    QUERY_GATE_VALUE_AT_CLICK_TIME_SUSPECT,
    StateVitalBitVariant,
    SUSPECT_STUBS,
    SuspectHypothesisStub,
    build_variant_frame,
    build_variant_payload,
    guaranteed_hidden_variant_ids,
    guaranteed_visible_variant_ids,
    iter_state_vital_bit_variants,
    observed_button_visible,
)


class StateVitalBitVariantGenerationTests(unittest.TestCase):
    def test_yields_at_least_one_variant_per_named_field_plus_baseline(self):
        variants = list(iter_state_vital_bit_variants())
        # baseline + first-byte + second-byte + both-bytes + 8 u32 bits +
        # u32-max + all-fields-1 == 14
        self.assertEqual(len(variants), 14)

    def test_variant_ids_are_unique(self):
        variants = list(iter_state_vital_bit_variants())
        ids = [v.variant_id for v in variants]
        self.assertEqual(len(ids), len(set(ids)), f"duplicate variant_id in {ids}")

    def test_baseline_variant_is_all_zero(self):
        variants = {v.variant_id: v for v in iter_state_vital_bit_variants()}
        baseline = variants["baseline-all-zero"]
        self.assertEqual(
            (baseline.field_0x0b_first, baseline.field_0x0b_second, baseline.field_0x14),
            (0, 0, 0),
        )

    def test_u32_bit_variants_cover_bits_0_through_7_only(self):
        variants = {v.variant_id: v for v in iter_state_vital_bit_variants()}
        for bit in range(8):
            key = f"u32-bit{bit}"
            self.assertIn(key, variants)
            self.assertEqual(variants[key].field_0x14, 1 << bit)
        # deliberately not covered this round -- see module docstring
        self.assertNotIn("u32-bit8", variants)
        self.assertNotIn("u32-bit31", variants)

    def test_u32_max_boundary_variant_present(self):
        variants = {v.variant_id: v for v in iter_state_vital_bit_variants()}
        self.assertEqual(variants["u32-max"].field_0x14, 0xFFFFFFFF)

    def test_each_variant_carries_a_non_empty_note(self):
        for variant in iter_state_vital_bit_variants():
            self.assertTrue(variant.note, f"{variant.variant_id} has an empty note")


class StateVitalBitVariantFieldRangeTests(unittest.TestCase):
    def test_no_generated_variant_exceeds_field_widths(self):
        # Guards against a future edit widening the generator past what
        # gm.state_wire.make_gm_update_state_payload accepts (u8/u8/u32).
        for variant in iter_state_vital_bit_variants():
            self.assertTrue(0 <= variant.field_0x0b_first <= 0xFF)
            self.assertTrue(0 <= variant.field_0x0b_second <= 0xFF)
            self.assertTrue(0 <= variant.field_0x14 <= 0xFFFFFFFF)


class BuildVariantPayloadTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_delegates_byte_for_byte_to_state_wire_payload_builder(self):
        variant = StateVitalBitVariant("t", 1, 0, 7, "test variant")
        got = build_variant_payload(self.legacy, variant)
        expected = make_gm_update_state_payload(self.legacy, 1, 0, 7)
        self.assertEqual(got, expected)

    def test_every_generated_variant_builds_a_nine_byte_payload(self):
        for variant in iter_state_vital_bit_variants():
            payload = build_variant_payload(self.legacy, variant)
            self.assertEqual(len(payload), 9, f"{variant.variant_id} payload not 9 bytes")

    def test_baseline_and_bit0_variants_differ_only_in_the_u32_field_bytes(self):
        variants = {v.variant_id: v for v in iter_state_vital_bit_variants()}
        baseline_payload = build_variant_payload(self.legacy, variants["baseline-all-zero"])
        bit0_payload = build_variant_payload(self.legacy, variants["u32-bit0"])
        # first four bytes (two u8tag pairs) must be identical -- only the
        # u32tag's value bytes (offset 5..8) may differ
        self.assertEqual(baseline_payload[:5], bit0_payload[:5])
        self.assertNotEqual(baseline_payload[5:], bit0_payload[5:])


class BuildVariantFrameTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_delegates_byte_for_byte_to_state_wire_frame_builder(self):
        variant = StateVitalBitVariant("t", 1, 0, 0, "test variant")
        pc, frame = build_variant_frame(self.legacy, variant)
        expected_pc, expected_frame = make_gm_update_state_frame(self.legacy, 0, 1, 0, 0)
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_default_vital_version_is_the_re105_confirmed_zero(self):
        variant = StateVitalBitVariant("t", 0, 0, 0, "test variant")
        pc, _frame = build_variant_frame(self.legacy, variant)
        expected_pc, _expected_frame = make_gm_update_state_frame(self.legacy, 0, 0, 0, 0)
        self.assertEqual(pc, expected_pc)

    def test_caller_can_override_vital_version(self):
        variant = StateVitalBitVariant("t", 0, 0, 0, "test variant")
        pc, _frame = build_variant_frame(self.legacy, variant, vital_version=4)
        expected_pc, _expected_frame = make_gm_update_state_frame(self.legacy, 4, 0, 0, 0)
        self.assertEqual(pc, expected_pc)

    def test_every_generated_variant_builds_the_pinned_41_byte_frame(self):
        # pf_bridge order letter 20260831_0152 names this the "pinned 41-byte
        # frame" -- regression guard that the envelope size stays fixed
        # across every variant this module generates.
        for variant in iter_state_vital_bit_variants():
            _pc, frame = build_variant_frame(self.legacy, variant)
            self.assertEqual(len(frame), 41, f"{variant.variant_id} frame not 41 bytes")

    def test_frame_still_carries_the_gm_update_state_vital_id(self):
        variant = StateVitalBitVariant("t", 1, 0, 0, "test variant")
        _pc, frame = build_variant_frame(self.legacy, variant)
        self.assertIn(GM_UPDATE_GM_STATE_VITAL_ID.to_bytes(2, "little"), frame)


class ObservedButtonVisibilityTests(unittest.TestCase):
    """GT-164 attended result (pf_bridge notes_to_chief
    20260831_0901_GT164-RESULT-...): field_0x0b_second == 1 -> BT_GM visible,
    14/14, no exception. These tests pin that table so a future edit to
    iter_state_vital_bit_variants cannot silently drift from it without a
    failing test -- they do NOT claim anything about click behaviour.
    """

    def test_visibility_tracks_field_0x0b_second_only(self):
        for variant in iter_state_vital_bit_variants():
            self.assertEqual(
                observed_button_visible(variant),
                variant.field_0x0b_second == 1,
                f"{variant.variant_id} visibility must track field_0x0b_second only",
            )

    def test_guaranteed_visible_ids_match_gt164s_reported_three(self):
        # GT-164's table: second-byte-1 / both-bytes-1 / all-fields-1 were the
        # only three of 14 variants with field_0x0b_second == 1.
        self.assertEqual(
            set(guaranteed_visible_variant_ids()),
            {"second-byte-1", "both-bytes-1", "all-fields-1"},
        )

    def test_guaranteed_hidden_ids_are_the_other_eleven(self):
        visible = set(guaranteed_visible_variant_ids())
        hidden = set(guaranteed_hidden_variant_ids())
        all_ids = {v.variant_id for v in iter_state_vital_bit_variants()}
        self.assertEqual(visible | hidden, all_ids)
        self.assertEqual(visible & hidden, set())
        self.assertEqual(len(hidden), 11)

    def test_field_0x0b_first_and_field_0x14_have_no_effect_on_visibility(self):
        # GT-164 nonclaim: neither field moved visibility in either direction,
        # including the field_0x14 all-ones boundary -- spot-check both ends.
        variants = {v.variant_id: v for v in iter_state_vital_bit_variants()}
        self.assertFalse(observed_button_visible(variants["first-byte-1"]))
        self.assertFalse(observed_button_visible(variants["u32-max"]))
        self.assertTrue(observed_button_visible(variants["all-fields-1"]))


class SuspectHypothesisStubTests(unittest.TestCase):
    """These stubs carry no frame, no bytes, no wire behaviour -- only
    verify their metadata shape, never their "truth" (there is none yet)."""

    def test_exactly_four_suspect_stubs(self):
        # suspect 4 named in the module docstring (create-path/factory
        # called) is the OUTCOME the click test observes, not an input
        # variant, so it never gets its own stub here. The fourth stub in
        # this tuple (gm-plugin-model-key) is a DIFFERENT, fifth question
        # added 2026-09-01 from Codex's GameMaster.dll loader RE -- see
        # module docstring "CODEX EVIDENCE ADDED".
        self.assertEqual(len(SUSPECT_STUBS), 4)

    def test_suspect_ids_match_the_order_letters_named_suspects(self):
        ids = {s.suspect_id for s in SUSPECT_STUBS}
        self.assertEqual(
            ids,
            {
                "connection-context",
                "query-0x25-gate-value-at-click-time",
                "current-ui-object-key-condition",
                "gm-plugin-model-key",
            },
        )

    def test_every_stub_carries_the_hypothesis_label(self):
        for stub in SUSPECT_STUBS:
            self.assertEqual(stub.label, HYPOTHESIS_LABEL)

    def test_every_stub_has_a_non_empty_question_and_reason(self):
        for stub in SUSPECT_STUBS:
            self.assertTrue(stub.question.strip())
            self.assertTrue(stub.why_not_wired_this_round.strip())

    def test_stubs_are_immutable_dataclasses(self):
        with self.assertRaises(Exception):
            CONNECTION_CONTEXT_SUSPECT.suspect_id = "different"  # type: ignore[misc]

    def test_named_stub_constants_are_exactly_the_four_in_the_tuple(self):
        self.assertEqual(
            set(SUSPECT_STUBS),
            {
                CONNECTION_CONTEXT_SUSPECT,
                QUERY_GATE_VALUE_AT_CLICK_TIME_SUSPECT,
                CURRENT_UI_OBJECT_KEY_SUSPECT,
                GM_PLUGIN_MODEL_KEY_SUSPECT,
            },
        )

    def test_stub_type_is_the_documented_dataclass(self):
        for stub in SUSPECT_STUBS:
            self.assertIsInstance(stub, SuspectHypothesisStub)

    def test_gm_plugin_model_key_suspect_cites_codex_0344_not_the_withdrawn_drafts(self):
        # This stub must trace to the AUTHORITATIVE letter (0344), never to
        # the two withdrawn drafts (0254/0321) it explicitly supersedes.
        self.assertIn("20260901_0344", GM_PLUGIN_MODEL_KEY_SUSPECT.question)
        self.assertNotIn("20260901_0254", GM_PLUGIN_MODEL_KEY_SUSPECT.question)
        self.assertNotIn("20260901_0321", GM_PLUGIN_MODEL_KEY_SUSPECT.question)

    def test_gm_plugin_model_key_suspect_hedges_as_proposed_not_proven(self):
        # Codex's own letter withdrew the absolute "not the DLL's original
        # return value" claim -- this stub must not overclaim in either
        # direction (neither "proven compat" nor "proven original").
        reason = GM_PLUGIN_MODEL_KEY_SUSPECT.why_not_wired_this_round.lower()
        self.assertIn("proposed", reason)
        question = GM_PLUGIN_MODEL_KEY_SUSPECT.question.lower()
        self.assertNotIn("proven original-dll", question)


if __name__ == "__main__":
    unittest.main()
