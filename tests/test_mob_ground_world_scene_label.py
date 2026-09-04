"""LANE-B round pcsjfr: the world line names a scene even when nothing fell.

WHAT WAS MEASURED.  Walking all twelve shipped ``Bg0003`` rows through
``strike`` -> ``kill`` -> ``loot_a_kill`` -> ``sustain_a_kill``, four of the
twelve rolled nothing and printed::

    MOB_GROUND_WORLD_REMEMBERED scene='' new=0 already_standing=0 refused=0 keys=none

``sustain_a_kill`` prints that line UNCONDITIONALLY and its own docstring
says why: "the floor was told" and "this seam never ran" are the two states
an attended round tells apart by grep.  A third of the grep's own output
naming no scene is a third of that discriminator missing for anybody
filtering a console by the scene under test -- and the number is not small
because roughly 38 pct of kills drop nothing by the shipped rates.

WHAT CHANGED.  ``remember_generation`` takes a LABEL for the case where no
row can name a scene, and ``sustain_a_kill`` passes the cell's own scene into
it.  A row still names its own scene whenever there is a row.

WHAT IS PINNED HERE, and the third one is the point of the file: the label
must never be able to become a second source of truth for the field that
decides which publication a row rides in.
"""
from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_drop_presence                  # noqa: E402
from pirateforce_foundation import mob_ground_persistence as ground   # noqa: E402
from pirateforce_foundation import mob_loot                           # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy          # noqa: E402

V141 = ROOT / "current/pf_login_game_server_v141.py"

SCENE = "Bg0002"
OTHER_SCENE = "Bg0003"
#: The Energy Cubic Crystal, a real mined id, so ``GroundDrop``'s own
#: known-item check passes.
CRYSTAL = 2400047


def a_drop(key: int, scene: str = SCENE) -> mob_loot.GroundDrop:
    return mob_loot.GroundDrop(
        drop_key=key, item_id=CRYSTAL, quantity=1,
        x=10.5, y=-20.25, z=30.75,
        mob_identity=0x203D, killer_identity=0x750059, scene=scene)


class TheLabelFillsOnlyWhereNoRowCanAnswerTests(unittest.TestCase):

    def test_an_empty_generation_carries_the_label(self):
        outcome = ground.remember_generation(
            (), scene_when_no_row_names_one=SCENE)
        self.assertEqual(outcome.scene, SCENE)
        self.assertEqual(outcome.remembered, ())
        self.assertEqual(outcome.reason, "")
        self.assertIn("scene=%r" % SCENE, ground.describe_remembered(outcome))

    def test_an_empty_generation_with_no_label_reads_as_it_always_did(self):
        outcome = ground.remember_generation(())
        self.assertEqual(outcome.scene, "")

    def test_a_row_beats_the_label_and_the_label_never_overrides_it(self):
        floor = ground.WorldGround()
        outcome = ground.remember_generation(
            (a_drop(0x1900A1),), world=floor,
            scene_when_no_row_names_one=OTHER_SCENE)
        self.assertEqual(outcome.scene, SCENE)
        self.assertEqual(len(outcome.remembered), 1)
        self.assertEqual(outcome.remembered[0].scene, SCENE)
        # And the row went to the scene it names, not to the label's.
        self.assertEqual(len(floor.standing(SCENE)), 1)
        self.assertEqual(len(floor.standing(OTHER_SCENE)), 0)

    def test_a_refusal_before_the_rows_are_read_still_names_the_scene(self):
        class Unreadable:
            def __iter__(self):
                raise RuntimeError("not a sequence")

        outcome = ground.remember_generation(
            Unreadable(), scene_when_no_row_names_one=SCENE)
        self.assertEqual(outcome.reason, ground.REFUSE_ROW_IS_NOT_A_DROP)
        self.assertEqual(outcome.scene, SCENE)

    def test_a_floor_that_raises_still_names_the_scene(self):
        class Angry(ground.WorldGround):
            def remember(self, rows):
                raise RuntimeError("floor is angry")

        outcome = ground.remember_generation(
            (a_drop(0x1900A2),), world=Angry(),
            scene_when_no_row_names_one=SCENE)
        self.assertTrue(outcome.reason.startswith(ground.REFUSE_CELL_RAISED))
        self.assertEqual(outcome.scene, SCENE)

    def test_a_label_that_is_not_a_scene_name_is_dropped_not_printed(self):
        """Anything but a non-empty ``str`` reads exactly as before.

        The value reaches a console line, so an object whose ``repr`` is a
        paragraph must not be able to get into one.
        """
        for junk in (None, 3, b"Bg0002", ["Bg0002"], "", object()):
            outcome = ground.remember_generation(
                (), scene_when_no_row_names_one=junk)
            self.assertEqual(outcome.scene, "", repr(junk))
            line = ground.describe_remembered(outcome)
            line.encode("ascii")
            self.assertIn("scene=''", line)


class TheKillThatDropsNothingNamesItsSceneTests(unittest.TestCase):
    """End to end through the function a kill's dispatch really calls."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)

    def _sustain(self, drops):
        cell = mob_loot.DropLedgerCell()
        cell.enter_scene(SCENE)
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            with contextlib.redirect_stdout(buffer):
                mob_drop_presence.sustain_a_kill(
                    cell, self.legacy, drops, world=ground.WorldGround())
        return buffer.getvalue()

    def test_a_kill_that_dropped_nothing_prints_the_cell_scene(self):
        printed = self._sustain(())
        self.assertIn(ground.WORLD_REMEMBERED_TOKEN, printed)
        self.assertIn("scene=%r" % SCENE, printed)
        self.assertNotIn("scene=''", printed)
        self.assertIn("new=0", printed)
        self.assertIn("keys=none", printed)

    def test_a_kill_that_dropped_something_is_unchanged(self):
        printed = self._sustain((a_drop(0x1900A3),))
        self.assertIn("scene=%r" % SCENE, printed)
        self.assertIn("new=1", printed)
        self.assertIn("0x1900A3", printed)

    def test_a_cell_whose_scene_raises_costs_nobody_their_drop(self):
        """The label is read in its own ``try``; it may never become a path.

        ``sustain_a_kill`` sits under an inbound frame from a stranger by way
        of the death dispatch, and the world half is a REPORT: a cell that
        cannot say which scene it is in still gets its rows remembered and
        still reaches its own composing path.  The label goes back to empty
        -- which is what the line said for every kill before this round --
        and nothing else about the call changes.

        The property is replaced ON THE REAL CLASS rather than on a subclass,
        because ``sustain_a_kill`` reads the cell through ``isinstance`` and a
        subclass would be accepted while a wrapper would not: the point is to
        drive the ``try`` around the label read, not to find out what a
        stand-in does.
        """
        angry = property(lambda self: (_ for _ in ()).throw(
            RuntimeError("no scene for you")))
        original = mob_loot.DropLedgerCell.current_scene
        mob_loot.DropLedgerCell.current_scene = angry
        self.addCleanup(
            setattr, mob_loot.DropLedgerCell, "current_scene", original)

        cell = mob_loot.DropLedgerCell()
        floor = ground.WorldGround()
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            with contextlib.redirect_stdout(buffer):
                step = mob_drop_presence.sustain_a_kill(
                    cell, self.legacy, (a_drop(0x1900A4),), world=floor)
        printed = buffer.getvalue()
        self.assertIn(ground.WORLD_REMEMBERED_TOKEN, printed)
        # The ROW named the scene, so the line names it even here.
        self.assertIn("scene=%r" % SCENE, printed)
        self.assertEqual(len(floor.standing(SCENE)), 1)
        self.assertIs(type(step), mob_drop_presence.PresenceStep)


if __name__ == "__main__":
    unittest.main()
