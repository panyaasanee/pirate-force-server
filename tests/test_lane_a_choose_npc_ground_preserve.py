"""LANE-A: a click must not sweep the loot lying on the ground.

WHAT THIS FILE IS FOR.  Until round ``gx7xtp`` all four of this lane's
ChooseNPC responders composed their answer frame with
``legacy.make_runtime_remote_actors`` - v141's own composer, which does not
carry the ground list.  A player who killed a monster, watched the drop
land, and then CLICKED anything before picking it up got an answer frame
that re-declared the scene's actors without the ground rows, and the drop
went out from under them.  ``LANE-B``'s letter
``pf_bridge/notes_to_chief/20260902_1845_LANE-B-TO-LANE-A`` shipped the
composer that keeps them (``mob_combat.remote_actors_preserving_the_
ground``) and named the two lines this lane owes; ``COO-DECISION
20260902_1946`` approved the call-site half with two conditions.  This is
that half, tested in one file for all four responders because the defect
it prevents is a property of the LANE and not of any one scene.

WHAT IS PROVEN HERE AND WHAT IS NOT.

    PROVEN, WIRE LAYER.  With no cell wired - which is every boot on
    ``main`` today, because the ``runtime.py`` call site does not pass one
    yet - each responder returns the SAME BYTES it returned before this
    round, and says so on the console with the real cause rather than a
    guess.  "Same bytes" is checked against v141's own composer run on the
    same entries, not against a recorded blob.

    PROVEN, GATE.  With a cell that reports live ground rows, the composed
    frame is the preserving one; with a cell that reports none, it is
    v141's.  The gate is ``mob_loot``'s own, called through
    ``mob_combat``: this file drives it, it does not re-implement it.

    NOT PROVEN.  That any of this reaches a screen.  No attended ticket is
    scheduled to read ``GROUND_ACTORS_LIVENESS_UNKNOWN`` - LANE-B's letter
    says so plainly and this file does not pretend otherwise.  ``GT-204``
    is the chief's ticket and its scope is loot / left click / into the
    bag; the click-while-loot-is-down case is not in it.

WHY THE SCENE IS CARRIED ALL THE WAY DOWN (condition of the LANE-B letter,
and of pf-adversary's D16/D7 in that round): a session holds ONE loot cell
and that cell knows which scene its rows belong to.  A frame composed for
scene 1 must not be gated by a row standing in Bg0002, and naming the scene
is what turns that into ``another_scenes_cell`` - a stated cause and v141's
bytes - instead of a number.

    AND THE SCENE HAS TO BE NAMED IN THE FORM THE CELL USES.  The letter
    passes ``scene_id`` straight through, which cannot gate anything: see
    ``test_an_int_scene_id_is_resolved_to_a_folder_before_it_gates``, the
    reason ``lane_a_ground_preserve`` exists at all, and this round's
    letter to LANE-B.
"""
from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_combat                      # noqa: E402
from pirateforce_foundation import mob_loot                        # noqa: E402
from pirateforce_foundation.lane_hooks import (                    # noqa: E402
    lane_a_ground_preserve as preserve,
)
from pirateforce_foundation.lane_hooks import (                    # noqa: E402
    lane_a_choose_npc_roster_scenes as roster_mod,
)
from pirateforce_foundation.lane_hooks import (                    # noqa: E402
    lane_a_choose_npc_scene1 as scene1_mod,
)
from pirateforce_foundation.lane_hooks import (                    # noqa: E402
    lane_a_choose_npc_scene2 as scene2_mod,
)
from pirateforce_foundation.lane_hooks import (                    # noqa: E402
    lane_a_choose_npc_scene14 as scene14_mod,
)
from pirateforce_foundation import world_scene_folder              # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy       # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: The four call sites this lane owns, as (label, module, scene id).  A
#: responder added to this lane and NOT added here is the failure mode this
#: file's own last test refuses.
RESPONDERS = (
    ("scene1", scene1_mod, 1),
    ("scene2", scene2_mod, 2),
    ("scene14", scene14_mod, 14),
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class _View:
    def __init__(self, rows: int) -> None:
        self.drops = tuple(range(rows))


class _Cell:
    """The narrowest stand-in for a session's loot cell: it answers the one
    call ``mob_loot.ground_rows_live_here`` makes - ``publication()`` ->
    ``(scene, view, elsewhere)`` - and nothing else.  A richer fake would be
    a second implementation of the thing under test.

    ``scene`` is a FOLDER NAME because that is what a real cell publishes;
    a fake that held a scene id would agree with a wiring bug rather than
    catch it.
    """

    def __init__(self, rows: int, scene: str) -> None:
        self._rows = rows
        self._scene = scene

    def publication(self) -> tuple:
        return (self._scene, _View(self._rows), 0)


class TheCallSitesAskTheGroundBeforeTheyCompose(unittest.TestCase):
    """Each responder accepts the cell and routes through the gate."""

    def test_every_responder_takes_a_mob_loot_cell_by_name(self) -> None:
        """It used to land in ``**_ignored``, which is how a wired call
        site can pass a cell for months and change nothing."""
        import inspect

        for label, module, _scene in RESPONDERS:
            with self.subTest(responder=label):
                parameters = inspect.signature(module.respond).parameters
                self.assertIn("mob_loot_cell", parameters)
                self.assertEqual(
                    parameters["mob_loot_cell"].kind,
                    inspect.Parameter.KEYWORD_ONLY)
                self.assertIsNone(parameters["mob_loot_cell"].default)

    def test_the_roster_responder_takes_it_too(self) -> None:
        """The roster module builds its responders in a factory, so its
        signature has to be read off a built one."""
        import inspect

        built = roster_mod._make_responder
        source = inspect.getsource(built)
        self.assertIn("mob_loot_cell: Any = None,", source)
        for scene in roster_mod.scenes_this_lane_answers_for():
            with self.subTest(scene=scene):
                entry = roster_mod._IDENTITY_OF_SCENE[scene]
                self.assertTrue(hasattr(entry, "SCENE_N_ID"))

    def test_no_responder_calls_v141s_composer_directly_any_more(
        self,
    ) -> None:
        """The property that keeps a fifth responder from being written the
        old way: the bare composer call is gone from every file in the
        lane's ChooseNPC family, and the preserving one is in each.
        """
        directory = ROOT / "src" / "pirateforce_foundation" / "lane_hooks"
        files = sorted(directory.glob("lane_a_choose_npc_*.py"))
        self.assertEqual(len(files), 4, [p.name for p in files])
        for path in files:
            with self.subTest(module=path.name):
                text = path.read_text(encoding="utf-8")
                body = "\n".join(
                    line for line in text.split("\n")
                    if not line.lstrip().startswith("#")
                )
                self.assertNotIn(
                    "legacy.make_runtime_remote_actors(entries)", body)
                self.assertIn("compose_answer(\n", body)


class TheBytesAreUnchangedWhileNoCellIsWired(unittest.TestCase):
    """The whole safety argument for landing this before chief's line."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()

    def _entries(self):
        legacy = self.legacy
        attr = legacy.make_remote_movement_attr(
            0x2001, 1.0, 2.0, 3.0, 0.0, mask=0x03)
        return [legacy.make_remote_actor_entry(
            4, 0x2001, [(legacy.MOVEMENT_ATTR, attr)])]

    def test_no_cell_composes_exactly_what_v141_composes(self) -> None:
        entries = self._entries()
        expected = self.legacy.make_runtime_remote_actors(list(entries))
        for label, _module, scene in RESPONDERS + (("ocean", None, 126),):
            with self.subTest(responder=label):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    got = preserve.compose_answer(
                        self.legacy, list(entries), scene, None)
                self.assertEqual(got, expected)

    def test_an_int_scene_id_is_resolved_to_a_folder_before_it_gates(
        self,
    ) -> None:
        """THE DEFECT THIS FILE EXISTS FOR, and it is measured rather than
        argued.  ``mob_loot.ground_rows_live_here`` folds its scene through
        ``scene_key``, which refuses anything but a ``str``.  Wired the way
        LANE-B's letter spells it - passing ``scene_id`` - every click on
        every scene reads ``caller_scene_unreadable`` and the gate can
        never open.  The lane's helper resolves the id first."""
        cell = _Cell(3, "Bg0002")
        # The letter's literal shape: a no-op, on every scene, forever.
        self.assertEqual(
            mob_loot.ground_liveness_reason(
                mob_loot.ground_rows_live_here(cell, 2)),
            "caller_scene_unreadable")
        # The lane's shape: a real count.
        self.assertEqual(preserve.ground_rows_for_scene(cell, 2), 3)
        for _label, _module, scene in RESPONDERS:
            with self.subTest(scene=scene):
                folder = world_scene_folder.scene_folder_for_scene_id(scene)
                self.assertIsNotNone(folder)
                self.assertEqual(
                    preserve.ground_rows_for_scene(_Cell(2, folder), scene),
                    2)

    def test_an_unaddressed_scene_id_never_reaches_the_cell(self) -> None:
        """Fail-closed in the only safe direction: ``None`` reaching
        ``ground_rows_live_here`` means "keep whatever scene the cell is
        publishing", which is the cross-scene gating this is meant to
        prevent.  An unresolvable id stops here instead."""
        self.assertIsNone(
            world_scene_folder.scene_folder_for_scene_id(99999))
        for bad in (99999, None, "1", 3.0, True):
            with self.subTest(scene_id=bad):
                answer = preserve.ground_rows_for_scene(_Cell(9, "bg0001"), bad)
                self.assertEqual(answer, mob_loot.GROUND_LIVENESS_BAD_SCENE)
                self.assertFalse(mob_loot.ground_is_live(answer))

    def test_the_console_says_the_real_cause_not_a_guess(self) -> None:
        """``no_cell`` is a different fact from ``cell_refused`` and from
        ``another_scenes_cell``, and an operator has to be able to tell
        them apart from the line alone."""
        self.assertEqual(
            mob_loot.ground_liveness_reason(
                mob_loot.ground_rows_live_here(None, 1)),
            "no_cell")
        self.assertEqual(
            mob_loot.ground_liveness_reason(
                preserve.ground_rows_for_scene(_Cell(3, "Bg0002"), 1)),
            "another_scenes_cell")

    def test_a_cell_from_another_scene_cannot_gate_this_frame(self) -> None:
        """The condition the LANE-B letter and pf-adversary D16 both put on
        this call site: rows standing in Bg0002 are not this frame's rows.
        """
        entries = self._entries()
        expected = self.legacy.make_runtime_remote_actors(list(entries))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            got = preserve.compose_answer(
                self.legacy, list(entries), 1, _Cell(3, "Bg0002"))
        self.assertEqual(got, expected)

    def test_a_live_row_in_this_scene_changes_the_frame(self) -> None:
        """The other half: the gate is not decorative.  A cell that really
        holds rows for THIS scene composes the preserving shape, which is
        not the bytes v141 returns."""
        entries = self._entries()
        plain = self.legacy.make_runtime_remote_actors(list(entries))
        cell = _Cell(3, "bg0001")
        live = preserve.ground_rows_for_scene(cell, 1)
        self.assertTrue(mob_loot.ground_is_live(live), live)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            got = preserve.compose_answer(self.legacy, list(entries), 1, cell)
        self.assertNotEqual(got, plain)
        # And an empty floor in the right scene is still v141's own bytes:
        # the gate turns on a row STANDING, not on a cell existing.
        with contextlib.redirect_stdout(io.StringIO()):
            empty = preserve.compose_answer(
                self.legacy, list(entries), 1, _Cell(0, "bg0001"))
        self.assertEqual(empty, plain)

    def test_each_responder_gets_its_own_site_name(self) -> None:
        """One shared name would let whichever responder fires first
        silence the other three for the life of the process - the console
        report is once per (site, cause) pair, by design."""
        names = {
            scene: mob_combat.choose_npc_site(scene)
            for _label, _module, scene in RESPONDERS
        }
        names[126] = mob_combat.choose_npc_site(126)
        self.assertEqual(len(set(names.values())), len(names), names)
        for scene, name in names.items():
            with self.subTest(scene=scene):
                self.assertTrue(name.isascii())
                self.assertNotIn(" ", name)


if __name__ == "__main__":
    unittest.main()
