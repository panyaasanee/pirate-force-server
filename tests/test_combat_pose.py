"""``combat_pose``: the production attack-pose crosswalk.

This file is the test ``pose_trial.py``'s own comment asked for in writing --
"Anyone who lands the tables here should replace this comment with a test that
re-derives the six rows" -- and it kills the mutant pf-adversary measured
surviving there (D3: changing 280 to 281 left the whole suite green).  Every
number below is asserted against the committed table copy, never against a
second typed-in constant, so a mistyped row fails here.
"""
import hashlib
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402
from pirateforce_foundation import combat_pose  # noqa: E402


class CrosswalkDerivationTests(unittest.TestCase):
    """The six rows, re-derived from the committed copy."""

    def test_every_kind_that_swings_comes_off_the_equip_value_copy(self):
        # Read the file back independently of the module's own loader, so a
        # bug in that loader cannot make this test agree with itself.
        text = (ROOT / "src/pirateforce_foundation/data/"
                "equip_value_attack_behavior.tsv").read_text(encoding="ascii")
        rows = [line.split("\t") for line in text.strip().splitlines()[1:]]
        derived = {
            int(equip_type): int(behavior)
            for _id, equip_type, behavior in rows if int(behavior)
        }
        self.assertEqual(combat_pose.ATTACK_BEHAVIOR_BY_EQUIP_TYPE, derived)
        # And the six rows themselves, spelled out: this is the assertion the
        # hand-typed table in pose_trial.py had no way to make.
        self.assertEqual(
            derived, {1: 280, 2: 284, 8: 288, 16: 282, 32: 290, 64: 286})

    def test_the_eleven_kinds_that_do_not_swing_are_absent_not_zero(self):
        # n_ATTACK_SKILL 0 means "this kind has no attack".  A lookup that
        # returned 0 would put selector 0 on the wire.
        self.assertNotIn(4, combat_pose.ATTACK_BEHAVIOR_BY_EQUIP_TYPE)  # shield
        self.assertNotIn(512, combat_pose.ATTACK_BEHAVIOR_BY_EQUIP_TYPE)  # chest
        self.assertEqual(len(combat_pose.ATTACK_BEHAVIOR_BY_EQUIP_TYPE), 6)
        self.assertNotIn(0, combat_pose.ATTACK_BEHAVIOR_BY_EQUIP_TYPE.values())

    def test_each_class_starting_right_hand_resolves_to_one_equip_type(self):
        self.assertEqual(
            combat_pose.EQUIP_TYPE_BY_CLASS_ID,
            {1: 1, 2: 2, 4: 16, 16: 8, 32: 64})

    def test_the_crosswalk_end_to_end_matches_the_class_names(self):
        """A fourth direction nobody arranged.

        The class names come from ``CHARCREATE_CLASS.s_ICON`` (LANE-CS's
        ``class_catalog``); the animations come from the attended screen.  The
        crosswalk was derived from neither, and they agree: the Gladiator
        swings a sword, the Paladin a mace, the Sniper fires a shot, the
        Necromancer throws the electric ball.
        """
        from pirateforce_foundation import class_catalog
        pairs = {}
        for class_id, name in class_catalog.CLASS_ID_TO_NAME.items():
            equip_type = combat_pose.equip_type_for_class(class_id)
            pairs[name] = combat_pose.behavior_for_equip_type(equip_type)
        self.assertEqual(pairs, {
            "Gladiator": 280,     # sword swing, GT-247 hits 2/9/16
            "Paladin": 284,       # mace swing, hits 3/10/17
            "Sniper": 282,        # gunshot, hits 5/12
            "Necromancer": 288,   # electric ball, hits 4/11
            "Sorcerer": 286,      # NOTHING on screen, hits 7/14
        })

    def test_no_class_starts_with_the_kind_that_swings_290(self):
        # 290 is screen-confirmed but is the voodoo doll's, and no selectable
        # class starts with one -- so it is reachable only once an equipped
        # item can differ from the class default.  Pinned so that seam is not
        # closed by accident.
        self.assertNotIn(32, combat_pose.EQUIP_TYPE_BY_CLASS_ID.values())
        self.assertEqual(combat_pose.behavior_for_equip_type(32), 290)


class ScreenConfirmationTests(unittest.TestCase):
    """COO-DECISION 20260905_1153 item 4: only what an owner watched."""

    def test_the_five_confirmed_ids_are_the_five_that_produced_a_pose(self):
        self.assertEqual(
            combat_pose.SCREEN_CONFIRMED_BEHAVIOR_IDS,
            frozenset({280, 284, 288, 282, 290}))

    def test_286_is_measured_negative_not_merely_untested(self):
        # The distinction matters: an id nobody tried would be a gap to close
        # with another attended run.  286 HAD its run, three times, and played
        # nothing -- so it is [PROPOSED] and stays out of production until
        # something explains it.
        self.assertIn(286, combat_pose.PROPOSED_BEHAVIOR_IDS)
        self.assertNotIn(286, combat_pose.SCREEN_CONFIRMED_BEHAVIOR_IDS)
        self.assertIn(286, combat_pose.ATTACK_BEHAVIOR_BY_EQUIP_TYPE.values())

    def test_the_inherited_echo_is_never_a_production_selector(self):
        self.assertFalse(
            combat_pose.is_screen_confirmed(combat_pose.INHERITED_ECHO_SELECTOR))

    def test_every_confirmed_id_is_a_row_of_the_committed_table(self):
        behaviors = set(combat_pose.ATTACK_BEHAVIOR_BY_EQUIP_TYPE.values())
        self.assertTrue(
            combat_pose.SCREEN_CONFIRMED_BEHAVIOR_IDS <= behaviors,
            "a screen-confirmed id that no equipment kind carries would be a "
            "number this lane invented")


class ProductionResolutionTests(unittest.TestCase):
    def test_a_gladiator_gets_the_sword_swing_and_says_so(self):
        behavior, line = combat_pose.production_behavior_for_class(1)
        self.assertEqual(behavior, 280)
        self.assertEqual(
            line, "POSE_PRODUCTION class=1 equip_type=1 base=2 behavior=280")

    def test_all_four_confirmed_classes_resolve(self):
        self.assertEqual(
            {class_id: combat_pose.production_behavior_for_class(class_id)[0]
             for class_id in (1, 2, 4, 16)},
            {1: 280, 2: 284, 4: 282, 16: 288})

    def test_the_sorcerer_is_refused_by_the_screen_result_not_by_a_gap(self):
        behavior, line = combat_pose.production_behavior_for_class(32)
        self.assertIsNone(behavior)
        self.assertEqual(
            line,
            "POSE_REFUSED reason=behavior_not_screen_confirmed class=32 "
            "equip_type=64 behavior=286")
        # The table DOES have the answer for this class; the refusal is about
        # what the screen did with it.  If that ever flips to a provenance
        # complaint, the crosswalk broke and this test says which half.
        self.assertEqual(combat_pose.equip_type_for_class(32), 64)

    def test_no_class_id_refuses_with_the_token_the_decision_names(self):
        behavior, line = combat_pose.production_behavior_for_class(None)
        self.assertIsNone(behavior)
        self.assertEqual(line, "POSE_NO_EQUIP_PROVENANCE reason=no_class_id")

    def test_an_unknown_class_id_refuses_and_names_it(self):
        behavior, line = combat_pose.production_behavior_for_class(99)
        self.assertIsNone(behavior)
        self.assertEqual(
            line,
            "POSE_NO_EQUIP_PROVENANCE reason=class_not_in_creation_gear "
            "class=99")

    def test_nothing_a_caller_can_pass_raises(self):
        """Interlock X07: this runs inside state.dispatch() under a listener
        with no except handlers, so a caller bug must cost one hit's pose and
        never the accept loop."""
        for bad in (None, "1", 1.0, b"1", [1], {"class_id": 1}, object(),
                    -1, 0, True, 2 ** 64):
            with self.subTest(bad=bad):
                behavior, line = combat_pose.production_behavior_for_class(bad)
                self.assertIsInstance(line, str)
                if behavior is not None:
                    self.assertIn(behavior,
                                  combat_pose.SCREEN_CONFIRMED_BEHAVIOR_IDS)

    def test_a_non_integer_class_id_is_reported_by_type_not_by_value(self):
        # Same rule three other modules in this package learned by
        # measurement: a VALUE can carry a byte the cp874 console cannot
        # encode, and the encode error lands inside the print reporting it.
        class Hostile:
            def __str__(self):
                raise AssertionError("a console token must not render this")
        _behavior, line = combat_pose.production_behavior_for_class(Hostile())
        self.assertIn("<Hostile>", line)
        self.assertTrue(line.isascii())

    def test_every_console_line_is_ascii_and_single_token_headed(self):
        for class_id in (None, 1, 2, 4, 16, 32, 99):
            with self.subTest(class_id=class_id):
                _behavior, line = combat_pose.production_behavior_for_class(
                    class_id)
                self.assertTrue(line.isascii())
                self.assertEqual(len(line.splitlines()), 1)
                self.assertIn(line.split(" ")[0], {
                    combat_pose.POSE_PRODUCTION,
                    combat_pose.POSE_NO_EQUIP_PROVENANCE,
                    combat_pose.POSE_REFUSED,
                })


class SourcePinTests(unittest.TestCase):
    def test_both_committed_copies_match_their_pinned_sha256(self):
        for name, expected in (
            ("equip_value_attack_behavior.tsv",
             combat_pose.EQUIP_VALUE_SHA256),
            ("creation_gear_by_class.tsv", combat_pose.CREATION_GEAR_SHA256),
        ):
            with self.subTest(name=name):
                raw = (ROOT / "src/pirateforce_foundation/data" /
                       name).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)

    @BRIDGE_GAMEDATA.skip_unless_present()
    def test_the_generator_reproduces_the_shipped_tables_when_it_can_run(self):
        """Real drift detection, not just a self-hash.

        A SOURCE_SHA256 pin "keeps matching itself forever regardless of what
        pf_bridge does" (pf-adversary, round iazmrv).  This re-runs the
        extractor against the live bridge clone -- which also re-runs its
        three decode checks -- and fails if the committed copies are stale.
        """
        finished = subprocess.run(
            [sys.executable,
             str(ROOT / "tools/pf_equip_attack_behavior_extract.py"),
             "--check", "--gamedata",
             str(ROOT.parent / "pf_bridge" / "gamedata")],
            capture_output=True, text=True)
        self.assertEqual(
            finished.returncode, 0,
            "the shipped attack-behavior tables are not what a fresh mining "
            "produces:\n%s%s" % (finished.stdout, finished.stderr))


if __name__ == "__main__":
    unittest.main()
