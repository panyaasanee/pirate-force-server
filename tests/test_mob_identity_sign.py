"""LANE-B: the identity-sign law measured by GT-288 set 3 (R324A).

Every colour assertion here is a row the owner read off her own screen on
2026-09-08 between 12:39 and 13:05 +07:00, not a derivation this lane made.
The point of the corpus test is that :func:`expected_name_colour` is checked
against the SCREEN and not against itself: if someone edits the function to
say an enemy monster is pink, the twenty-four rows fail, not a paraphrase of
the function.
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_identity_sign as mis
from pirateforce_foundation.legacy_bridge import load_legacy


class TestR324ACorpus(unittest.TestCase):
    """The twenty-four boards, reproduced by the rule."""

    def test_every_measured_row_comes_back_out_of_the_rule(self):
        for label, sign, enemy, offensive, colour in mis.R324A_ROWS:
            with self.subTest(label=label):
                identity = {1: 0x2001, 0: 0, -1: -7}[sign]
                self.assertEqual(
                    mis.expected_name_colour(
                        identity,
                        faction_is_enemy=enemy,
                        offensive=offensive,
                    ),
                    colour,
                )

    def test_the_corpus_covers_all_five_colours_and_the_undrawn_case(self):
        self.assertEqual(
            {row[4] for row in mis.R324A_ROWS},
            {
                mis.NAME_COLOUR_GREEN, mis.NAME_COLOUR_PINK,
                mis.NAME_COLOUR_YELLOW, mis.NAME_COLOUR_ORANGE,
                mis.NAME_COLOUR_RED, mis.NAME_COLOUR_NOT_DRAWN,
            },
        )

    def test_the_corpus_is_the_twenty_four_boards_that_were_composed(self):
        labels = [row[0] for row in mis.R324A_ROWS]
        self.assertEqual(len(labels), 24)
        self.assertEqual(len(set(labels)), 24)

    def test_only_the_enemy_half_of_the_monster_band_names_a_shade(self):
        for label, sign, enemy, offensive, _ in mis.R324A_ROWS:
            with self.subTest(label=label):
                if sign == -1 and enemy:
                    self.assertIsInstance(offensive, bool)
                else:
                    self.assertIsNone(offensive)


class TestTheRuleRefusesRatherThanGuesses(unittest.TestCase):

    def test_an_enemy_monster_without_a_shade_field_is_refused(self):
        with self.assertRaises(mis.MobIdentitySignError):
            mis.expected_name_colour(-1, faction_is_enemy=True)

    def test_a_positive_identity_never_reaches_the_monster_colours(self):
        for enemy in (True, False):
            self.assertIn(
                mis.expected_name_colour(0x2001, faction_is_enemy=enemy),
                (mis.NAME_COLOUR_GREEN, mis.NAME_COLOUR_PINK),
            )

    def test_zero_is_not_drawn_whatever_else_it_carries(self):
        for enemy in (True, False):
            self.assertEqual(
                mis.expected_name_colour(0, faction_is_enemy=enemy),
                mis.NAME_COLOUR_NOT_DRAWN,
            )

    def test_a_bool_is_not_an_identity(self):
        with self.assertRaises(mis.MobIdentitySignError):
            mis.is_player_identity(True)


class TestTheAllocator(unittest.TestCase):

    def test_every_allocated_identity_is_in_the_monster_band(self):
        for scene_id in (0, 1, 2, 14, 126, 304, 305, 2047):
            for placement in (0, 1, 71, mis.SCENE_STRIDE - 1):
                identity = mis.mob_wire_identity(scene_id, placement)
                self.assertTrue(mis.is_mob_identity(identity))
                self.assertTrue(mis.identity_is_drawn(identity))
                self.assertFalse(mis.is_player_identity(identity))

    def test_round_trip(self):
        for scene_id in (0, 1, 14, 126, 2047):
            for placement in (0, 1, 71, mis.SCENE_STRIDE - 1):
                with self.subTest(scene=scene_id, placement=placement):
                    self.assertEqual(
                        mis.scene_and_placement_for(
                            mis.mob_wire_identity(scene_id, placement)),
                        (scene_id, placement),
                    )

    def test_two_scenes_cannot_collide(self):
        """The hazard ``field_mobs`` line ~1013 names, closed by construction."""
        seen = {}
        for scene_id in range(0, 400):
            for placement in range(0, 80):
                identity = mis.mob_wire_identity(scene_id, placement)
                self.assertNotIn(identity, seen)
                seen[identity] = (scene_id, placement)
        self.assertEqual(len(seen), 400 * 80)

    def test_a_placement_past_the_stride_is_refused_not_wrapped(self):
        with self.assertRaises(mis.MobIdentitySignError):
            mis.mob_wire_identity(1, mis.SCENE_STRIDE)

    def test_the_inverse_refuses_identities_it_could_not_have_made(self):
        for identity in (0, 1, 0x2001, mis.MOB_IDENTITY_FLOOR - 1):
            with self.subTest(identity=identity):
                with self.assertRaises(mis.MobIdentitySignError):
                    mis.scene_and_placement_for(identity)


class TestTheWireEncoding(unittest.TestCase):
    """A negative identity survives the FROZEN encoder, measured not assumed."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_the_module_agrees_with_v141_qwordtag_byte_for_byte(self):
        for identity in (
            1, 0x2001, -1, -7, -57345,
            mis.mob_wire_identity(14, 0), mis.MOB_IDENTITY_FLOOR,
        ):
            with self.subTest(identity=identity):
                self.assertEqual(
                    bytes(self.legacy.qwordtag(0x32, identity)),
                    bytes([0x32]) + mis.encode_wire_identity(identity),
                )

    def test_a_negative_identity_does_not_raise_in_the_frozen_encoder(self):
        # This is the fact the whole band rests on: v141 masks to two's
        # complement rather than packing an unsigned value, so the monster
        # band needs no second encoder.
        self.assertEqual(
            bytes(self.legacy.qwordtag(0x32, -1))[1:],
            b"\xff" * 8,
        )


class TestTheProductionRefusal(unittest.TestCase):

    def test_zero_is_refused_on_the_composition_path(self):
        with self.assertRaises(mis.MobIdentitySignError):
            mis.refuse_undrawable_identity(0)

    def test_a_drawable_identity_passes_through_unchanged(self):
        for identity in (0x2001, -1, mis.mob_wire_identity(14, 3)):
            self.assertEqual(mis.refuse_undrawable_identity(identity), identity)

    def test_the_hostile_composer_refuses_an_undrawable_monster(self):
        """The guard is on the real path, not only in this module."""
        from dataclasses import replace
        from pirateforce_foundation import field_mobs

        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        mob = field_mobs.load_roster()[0]
        # actor_identity is 0x2000 + placement_index + 1, so this is the
        # placement index that would produce identity 0.
        undrawable = replace(mob, placement_index=-0x2001)
        self.assertEqual(undrawable.actor_identity, 0)
        with self.assertRaises(mis.MobIdentitySignError):
            field_mobs.hostile_npc_attr(legacy, undrawable)


if __name__ == "__main__":
    unittest.main()
