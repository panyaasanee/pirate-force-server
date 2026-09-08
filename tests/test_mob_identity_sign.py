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

    def test_the_band_ascends_with_the_placement_index(self):
        """COO decision 1642 option 3, as the assertion the four readers need.

        Not "is negative" and not "is unique" -- ORDER.  ``load_roster``
        hands rows out in placement order, ``CombatLedger`` refuses a
        roster that is not ascending, ``open_register`` sorts by identity
        silently, and the census ships in roster order.
        """
        for scene_id in (0, 1, 14, 126, 999, mis.SCENE_ID_CEILING - 1):
            with self.subTest(scene=scene_id):
                rows = [
                    mis.mob_wire_identity(scene_id, placement)
                    for placement in range(0, 80)
                ]
                self.assertEqual(rows, sorted(rows))
                self.assertEqual(len(set(rows)), len(rows))

    def test_the_band_ascends_with_the_scene_id_too(self):
        """So a ledger that ever holds two scenes sorts the same way."""
        rows = [
            mis.mob_wire_identity(scene_id, placement)
            for scene_id in range(0, 40)
            for placement in range(0, 30)
        ]
        self.assertEqual(rows, sorted(rows))

    def test_every_scene_declares_a_block_that_holds_its_own_stride(self):
        for scene_id in (0, 1, 14, 999, mis.SCENE_ID_CEILING - 1):
            with self.subTest(scene=scene_id):
                first, last = mis.scene_band_bounds(scene_id)
                self.assertEqual(last - first + 1, mis.SCENE_STRIDE)
                self.assertEqual(
                    first, mis.mob_wire_identity(scene_id, 0))
                self.assertEqual(
                    last,
                    mis.mob_wire_identity(scene_id, mis.SCENE_STRIDE - 1))
                self.assertLess(last, 0)

    def test_no_scenes_block_runs_into_the_next(self):
        previous_last = None
        for scene_id in range(0, 200):
            first, last = mis.scene_band_bounds(scene_id)
            if previous_last is not None:
                self.assertEqual(first, previous_last + 1)
                self.assertGreater(first, previous_last)
            previous_last = last

    def test_a_scene_id_past_the_block_ceiling_is_refused_not_wrapped(self):
        """The overflow the COO approval names: loud, not folded back.

        Asserted as a REFUSAL and as a non-collision, because the failure
        being guarded against is not "an exception did not happen", it is
        "scene N quietly got scene 0's identities".
        """
        for scene_id in (
            mis.SCENE_ID_CEILING,
            mis.SCENE_ID_CEILING + 1,
            mis.SCENE_ID_CEILING * 4,
        ):
            with self.subTest(scene=scene_id):
                with self.assertRaises(mis.MobIdentitySignError):
                    mis.mob_wire_identity(scene_id, 0)
                with self.assertRaises(mis.MobIdentitySignError):
                    mis.scene_band_bounds(scene_id)

    def test_the_two_entry_points_refuse_the_same_scene_ids(self):
        """A block a caller can be told about is a block it can allocate in."""
        for scene_id in (-1, 0, 1, 999, mis.SCENE_ID_CEILING - 1,
                         mis.SCENE_ID_CEILING, True, "14"):
            with self.subTest(scene=scene_id):
                bounds_raised = allocator_raised = False
                try:
                    mis.scene_band_bounds(scene_id)
                except mis.MobIdentitySignError:
                    bounds_raised = True
                try:
                    mis.mob_wire_identity(scene_id, 0)
                except mis.MobIdentitySignError:
                    allocator_raised = True
                self.assertEqual(bounds_raised, allocator_raised)

    def test_every_scene_id_the_tree_names_fits_inside_the_ceiling(self):
        """The ceiling is a declared bound; this is the measurement under it."""
        from pirateforce_foundation.gm import scene_catalog

        known = sorted(scene_catalog.SCENE_ID_TO_NAME)
        self.assertTrue(known)
        self.assertLess(known[-1], mis.SCENE_ID_CEILING)
        for scene_id in known:
            self.assertTrue(mis.is_mob_identity(
                mis.mob_wire_identity(scene_id, 0)))

    def test_the_whole_band_stays_clear_of_the_floor(self):
        """Both ends, so widening one constant cannot silently cross it."""
        lowest = mis.mob_wire_identity(0, 0)
        highest = mis.mob_wire_identity(
            mis.SCENE_ID_CEILING - 1, mis.SCENE_STRIDE - 1)
        self.assertEqual(lowest, mis.MOB_IDENTITY_BASE)
        self.assertGreater(lowest, mis.MOB_IDENTITY_FLOOR)
        self.assertLess(highest, 0)
        self.assertEqual(highest, -(mis.SWEEP_RESERVED_IDENTITIES + 1))

    def test_the_inverse_refuses_identities_it_could_not_have_made(self):
        for identity in (0, 1, 0x2001, mis.MOB_IDENTITY_FLOOR - 1):
            with self.subTest(identity=identity):
                with self.assertRaises(mis.MobIdentitySignError):
                    mis.scene_and_placement_for(identity)


class TestTheWallBeatTwoWalksIntoTests(unittest.TestCase):
    """The shared world registry refuses every identity this band hands out.

    MEASURED THIS ROUND, not predicted.  ``world_scene_registry`` is
    LANE-A's book and this lane writes combat state INTO it (NOW.md: "A =
    registry - B writes combat state into A's registry"), so this lane may
    not change it.  Its ``_require_identity`` accepts ``1 <= identity <=
    0xFFFFFFFF``; every value :func:`mob_wire_identity` produces is
    negative, so ``note_position`` and ``note_balance`` come back with
    reason ``bad_identity`` and remember NOTHING.

    WHY THIS IS A PIN AND NOT A BUG REPORT.  Those two doors do not raise --
    they return a ``NoteOutcome``.  So the day beat 2 flips a scene onto the
    band, every monster in that scene stops being written to the shared
    world with no exception anywhere: the arrival census reads an empty
    book, and a second player entering the scene sees monsters standing at
    their table positions with full HP no matter what the first player did
    to them.  That is a silent player-visible defect, which is the exact
    shape this house pins in a test rather than leaves in prose.

    This test goes RED the day LANE-A widens the gate, and that is the day
    it should be rewritten to assert the new reach.  The ask is
    ``notes_to_chief/20260908_20xx_LANE-B-ASK-COO-the-world-registry-
    refuses-every-band-identity.md``.
    """

    def test_the_registry_refuses_a_band_identity_on_both_doors(self):
        from pirateforce_foundation import world_scene_registry as wsr

        registry = wsr.WorldSceneRegistry()
        identity = mis.mob_wire_identity(2, 0)
        self.assertLess(identity, 0)
        for outcome in (
            registry.note_position("Bg0002", identity, (1.0, 2.0, 3.0)),
            registry.note_balance("Bg0002", identity, 10, 20),
        ):
            self.assertEqual(outcome.reason, wsr.REFUSE_BAD_IDENTITY)
            self.assertIsNone(outcome.remembered)

    def test_it_is_the_sign_and_not_something_else_about_the_value(self):
        """The legacy positive formula goes in through the same door."""
        from pirateforce_foundation import world_scene_registry as wsr

        registry = wsr.WorldSceneRegistry()
        outcome = registry.note_position("Bg0002", 0x2001, (1.0, 2.0, 3.0))
        self.assertEqual(outcome.reason, "")
        self.assertIsNotNone(outcome.remembered)

    def test_the_refusal_is_returned_rather_than_raised(self):
        """Which is why nothing upstream would notice the loss."""
        from pirateforce_foundation import world_scene_registry as wsr

        registry = wsr.WorldSceneRegistry()
        identity = mis.mob_wire_identity(2, 5)
        outcome = registry.note_balance("Bg0002", identity, 1, 2)
        self.assertEqual(outcome.reason, wsr.REFUSE_BAD_IDENTITY)
        # nothing was written, and no caller was told by an exception
        self.assertEqual(registry.remembered("Bg0002"), ())


class TestTheBandDoesNotStealTheSweepsIdentities(unittest.TestCase):
    """pf-adversary round ``gadxq5``, finding D6.

    The first draft handed scene 0's first six placements -1..-6, which are
    exactly the six identities ``name_colour_sweep`` allocates to its
    attended rows.  Two actors sharing an identity overwrite each other on
    the client, and the board that survives answers a different question
    than the tester is reading.  This reads the sweep's real tuple, so
    shrinking the reserved head goes red here rather than on someone's
    screen.
    """

    def test_no_allocated_identity_lands_on_a_sweep_row(self):
        from pirateforce_foundation import name_colour_sweep as ncs

        sweep = {
            ncs.negative_identity_for(label)
            for label in ncs.NEGATIVE_IDENTITY_SLOTS
        }
        self.assertTrue(sweep)
        for scene_id in range(0, 40):
            for placement in range(0, 80):
                self.assertNotIn(
                    mis.mob_wire_identity(scene_id, placement), sweep)

    def test_the_reserved_head_covers_every_slot_the_sweep_declares(self):
        from pirateforce_foundation import name_colour_sweep as ncs

        self.assertGreaterEqual(
            mis.SWEEP_RESERVED_IDENTITIES, len(ncs.NEGATIVE_IDENTITY_SLOTS))

    def test_the_inverse_refuses_the_reserved_head_rather_than_decoding_it(self):
        for identity in (-1, -6, -mis.SWEEP_RESERVED_IDENTITIES):
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
