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

    PROVEN, PER CALL SITE.  Each responder is driven END TO END through
    ``respond()`` with and without a cell, and the console token it emits
    is read back.  That is what makes a mis-wired call site red:
    pf-adversary (round ``gx7xtp``, D3) showed that swapping the last two
    arguments, or passing ``None`` where the cell goes, left the whole
    7,158-test suite byte-identical when the only guard was a text scan.

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


class TheCellIsHeldBackUntilTheLockHoldingComposerLands(unittest.TestCase):
    """``COO-DECISION 20260902_1946`` approved the call site WITH two
    conditions - close the read-then-compose race, never sweep silently on
    a read - and LANE-B closed both in a LATER letter (``20260902_2048``)
    with a composer that is not on ``main``.  chief measured the same
    absence and declined to wire it (``20260902_2208``).  So a cell that
    arrives today is held back rather than asked, and these tests are what
    stop that from being a comment."""

    def test_the_lock_holding_composer_is_still_absent(self) -> None:
        """The premise of the hold, checked rather than assumed.  When this
        goes red the hold is over: delete it, and the branch it guards."""
        self.assertIsNone(preserve.under_publication_composer())
        self.assertFalse(hasattr(mob_combat, preserve.UNDER_PUBLICATION_COMPOSER))

    def test_a_cell_is_never_asked_while_the_composer_is_missing(
        self,
    ) -> None:
        """The cell object itself would raise if it were read, so this is
        not "the count came back unusable" - it is "nobody read it"."""
        class _Explodes:
            def publication(self):
                raise AssertionError("the cell was asked, and it must not be")

        legacy = _legacy()
        attr = legacy.make_remote_movement_attr(
            0x2001, 1.0, 2.0, 3.0, 0.0, mask=0x03)
        entries = [legacy.make_remote_actor_entry(
            4, 0x2001, [(legacy.MOVEMENT_ATTR, attr)])]
        expected = legacy.make_runtime_remote_actors(list(entries))
        preserve._HELD_BACK_REPORTED.clear()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            got = preserve.compose_answer(
                legacy, list(entries), 1, _Explodes())
        self.assertEqual(got, expected)
        self.assertIn(preserve.CELL_HELD_BACK_TOKEN, buffer.getvalue())

    def test_the_held_back_line_is_one_ascii_token_per_scene(self) -> None:
        legacy = _legacy()
        attr = legacy.make_remote_movement_attr(
            0x2001, 1.0, 2.0, 3.0, 0.0, mask=0x03)
        entries = [legacy.make_remote_actor_entry(
            4, 0x2001, [(legacy.MOVEMENT_ATTR, attr)])]
        preserve._HELD_BACK_REPORTED.clear()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            for _ in range(4):
                preserve.compose_answer(
                    legacy, list(entries), 1, _Cell(3, "bg0001"))
            preserve.compose_answer(
                legacy, list(entries), 2, _Cell(3, "Bg0002"))
        lines = [line for line in buffer.getvalue().split("\n")
                 if preserve.CELL_HELD_BACK_TOKEN in line]
        self.assertEqual(len(lines), 2, lines)
        for line in lines:
            with self.subTest(line=line):
                self.assertTrue(line.isascii())
                line.encode("cp874")
                self.assertIn("reason=", line)
                self.assertIn(preserve.UNDER_PUBLICATION_COMPOSER, line)


class EachResponderReallyPassesItsOwnCellAndItsOwnScene(unittest.TestCase):
    """pf-adversary D3, closed.  Every one of these drives the REAL
    ``respond()``, so a call site with its arguments swapped, or one that
    drops the cell on the floor, goes red HERE - which a text scan of the
    source could never do."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()

    def _drive(self, module, scene, cell):
        """Call a responder for real and return its console output.

        ``_placements_by_index`` takes the legacy handle in one module and
        nothing in the others; asked for both rather than special-cased by
        name, so a fifth responder joins without editing this."""
        try:
            placements = module._placements_by_index(self.legacy)
        except TypeError:
            placements = module._placements_by_index()
        indices = tuple(sorted(placements))
        preserve._HELD_BACK_REPORTED.clear()
        mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED.clear()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            answer = module.respond(
                legacy=self.legacy,
                chosen_identities=(0x2000 + indices[0] + 1,),
                population_indices=indices,
                last_target_pos=(0.0, 0.0, 0.0, 0.0),
                scene_id=scene,
                mob_loot_cell=cell,
            )
        return answer, buffer.getvalue()

    def test_no_cell_says_no_cell_and_a_cell_says_held_back(self) -> None:
        for label, module, scene in RESPONDERS:
            if not hasattr(module, "_placements_by_index"):
                continue
            with self.subTest(responder=label):
                answer, out = self._drive(module, scene, None)
                self.assertIsNotNone(answer)
                # No cell: the cause the console names is the wiring hole,
                # and it is NOT the held-back one.
                self.assertNotIn(preserve.CELL_HELD_BACK_TOKEN, out)
                self.assertIn("no_cell", out)

                folder = world_scene_folder.scene_folder_for_scene_id(scene)
                answer, out = self._drive(module, scene, _Cell(2, folder))
                self.assertIsNotNone(answer)
                # A cell that reached the gate flips the cause.  An
                # argument-swapped call site cannot produce this line, and
                # a call site that drops the cell produces "no_cell" here.
                self.assertIn(preserve.CELL_HELD_BACK_TOKEN, out)
                self.assertNotIn("no_cell", out)

    def test_the_frame_is_the_same_either_way_today(self) -> None:
        """Holding the cell back must cost the ground list, never bytes."""
        for label, module, scene in RESPONDERS:
            if not hasattr(module, "_placements_by_index"):
                continue
            with self.subTest(responder=label):
                without, _ = self._drive(module, scene, None)
                folder = world_scene_folder.scene_folder_for_scene_id(scene)
                with_cell, _ = self._drive(module, scene, _Cell(2, folder))
                self.assertEqual(without.pc, with_cell.pc)
                self.assertEqual(without.frame, with_cell.frame)


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

    def test_the_gate_itself_is_not_decorative(self) -> None:
        """The scene resolve really does turn a cell into a live count, and
        a live count really does compose different bytes.

        ``compose_answer`` deliberately does NOT reach that shape today -
        it holds the cell back until the lock-holding composer lands, see
        ``TheCellIsHeldBackUntilTheLockHoldingComposerLands`` - so this
        drives the two halves separately.  Collapsing them into one call
        is what the hold forbids, not what it hides.
        """
        entries = self._entries()
        plain = self.legacy.make_runtime_remote_actors(list(entries))
        live = preserve.ground_rows_for_scene(_Cell(3, "bg0001"), 1)
        self.assertTrue(mob_loot.ground_is_live(live), live)
        self.assertEqual(live, 3)
        with contextlib.redirect_stdout(io.StringIO()):
            preserved = mob_combat.remote_actors_preserving_the_ground(
                self.legacy, list(entries),
                mob_combat.choose_npc_site(1), ground_rows_left=live)
        self.assertNotEqual(preserved, plain)
        # An empty floor in the right scene is still v141's own bytes: the
        # gate turns on a row STANDING, not on a cell existing.
        empty = preserve.ground_rows_for_scene(_Cell(0, "bg0001"), 1)
        self.assertEqual(empty, 0)
        self.assertFalse(mob_loot.ground_is_live(empty))
        with contextlib.redirect_stdout(io.StringIO()):
            composed = mob_combat.remote_actors_preserving_the_ground(
                self.legacy, list(entries),
                mob_combat.choose_npc_site(1), ground_rows_left=empty)
        self.assertEqual(composed, plain)

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
