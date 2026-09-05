"""LANE-A round (this round): the ground-drop companion for a mid-combat
recompose -- R316 finding "kho" (the third labeled finding) (KA1A, pf_bridge/notes_to_chief/20260905_1102),
COO-DECISION 20260905_1152 item 2(1).

WHAT A PLAYER SEES, MEASURED ON A REAL CLIENT BEFORE THIS FIX (Panya,
attended, R316): kill monster A, watch two items land on the ground, hit
monster B for the first time -- and monster A's items vanish off the screen
at the exact moment ``MOB_COMBAT_BAR_CENSUS_RECOMPOSE`` fires, because that
frame carries no information about the floor and RE-130 says a generation
that omits a live key erases it on the client.

THIS FILE PINS TWO THINGS.

  1. THE BUG, AS A MEASURED FACT ABOUT THE BYTES rather than an assumption:
     ``mob_scene_recompose.recompose_frames`` has no channel for ground
     state at all -- ``SceneRecompose`` carries no ground-shaped field, and
     the bytes it composes for a hit on monster B are identical whether or
     not monster A's drops are standing on the floor.  So the recompose
     genuinely cannot be what preserves the floor; the fix has to be a
     second, additional frame.

  2. THE FIX: ``mob_scene_recompose.ground_companion_actions`` reuses the
     exact mechanism ``mob_drop_presence.reannounce_ground`` already proved
     correct for GT-242 (``sustain_a_kill(cell, legacy, ())``), returns the
     scene's live ground-drop rows as ready-to-queue actions, and never
     raises.

Removing :func:`mob_scene_recompose.ground_companion_actions` makes every
test in ``GroundCompanionActionsTests`` below fail with ``AttributeError`` --
that is this file's proof that the function is the fix, not merely a
description of one.
"""
from __future__ import annotations

import contextlib
import io
import random
import sys
import unittest
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import mob_drop_presence  # noqa: E402
from pirateforce_foundation import mob_loot  # noqa: E402
from pirateforce_foundation import mob_scene_recompose as recompose  # noqa: E402
from pirateforce_foundation import world_population_bg0002  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
ANCHOR = (10.0, 20.0, 30.0)
SCENE2 = world_population_bg0002.SCENE2_N_ID
SCENE2_FOLDER = field_mobs.BG0002_SCENE
KILLER = 0x750059


class _Clock:
    """A clock that only moves when a test says so."""

    def __init__(self, now=1000.0):
        self.now = float(now)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += float(seconds)


class GroundCompanionFixture(unittest.TestCase):
    """Real scene-2 tables, the real frozen serializer, a real drop cell.

    Two DIFFERENT monsters that each drop something -- the same search
    ``tests/test_mob_drop_presence_ground_reannounce.py`` already uses,
    reused here rather than a second hand-rolled copy, so this file's
    fixture cannot silently disagree with the one GT-242's own tests pin.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.roster = field_mobs.roster_for_scene_id(SCENE2)
        cls.ledger = mob_combat.open_ledger_for_scene_id(SCENE2)
        cls.anchor = recompose.census_anchor(
            SCENE2, ANCHOR, world_population_bg0002.DEFAULT_ACTOR_COUNT)
        cls.dropping = []
        for mob in cls.roster:
            for seed in range(60):
                roll = mob_loot.roll_drops(mob, random.Random(seed))
                if roll.placeable_count:
                    cls.dropping.append((mob, seed))
                    break
        if len(cls.dropping) < 2:
            raise unittest.SkipTest(
                "scene 2's tables do not drop for two distinct monsters "
                "with this seed search")

    def setUp(self):
        self.register = mob_death.DeathRegister()
        self.clock = _Clock()
        self.cell = mob_loot.DropLedgerCell(
            clock=self.clock, scene=SCENE2_FOLDER)

    def _drop_monster_a(self):
        mob_a, seed = self.dropping[0]
        drops = self.cell.loot_a_kill(
            mob_a,
            mob_death.DeathRecord(mob_a.actor_identity, KILLER, mob_a.max_hp),
            mob_loot.roll_drops(mob_a, random.Random(seed)),
            kill_token=1,
        )
        self.assertTrue(drops, "fixture needs monster A to leave a real drop")
        return drops


class RecomposeIsBlindToTheFloorTests(GroundCompanionFixture):
    """MEASURES THE BUG.  ``recompose_frames`` has no way to know the floor
    exists, so it cannot be the thing that keeps it on screen -- the fix has
    to be an additional frame, never a field on this one."""

    def test_scene_recompose_carries_no_ground_shaped_field(self):
        names = {f.name for f in fields(recompose.SceneRecompose)}
        leaking = {
            n for n in names
            if "ground" in n or "drop" in n or "loot" in n
        }
        self.assertEqual(
            leaking, set(),
            "SceneRecompose grew a ground-shaped field -- the companion "
            "wiring ask (GROUND_COMPANION_WIRING) and this test both need "
            "to be revisited before this assertion is simply deleted")

    def test_recompose_bytes_do_not_change_when_the_floor_gains_a_drop(self):
        before = recompose.recompose_frames(
            self.legacy, self.anchor, self.register, ledger=self.ledger)
        self.assertEqual(before.state, recompose.STATE_COMPOSED)
        self._drop_monster_a()
        after = recompose.recompose_frames(
            self.legacy, self.anchor, self.register, ledger=self.ledger)
        self.assertEqual(after.state, recompose.STATE_COMPOSED)
        # THIS is R316 finding "kho" (the third labeled finding), measured at the unit level: the census a
        # hit on monster B would recompose is byte-for-byte identical
        # whether or not monster A's drops are standing on the floor, so
        # nothing about this frame is what tells the client to keep them --
        # and nothing about it wipes them either.  The wipe RE-130 predicts
        # is a property of the CLIENT reading an actor collection that omits
        # a key it already drew, not of these bytes disagreeing with
        # anything.
        self.assertEqual(before.pc, after.pc)
        self.assertEqual(before.frame, after.frame)


class GroundCompanionActionsTests(GroundCompanionFixture):
    """THE FIX.  Removing ``ground_companion_actions`` fails every test in
    this class with ``AttributeError`` -- that failure IS this file's proof
    that the function is the fix and not a description of one."""

    def test_returns_an_explicit_empty_tuple_for_a_bare_floor(self):
        result = recompose.ground_companion_actions(self.cell, self.legacy)
        self.assertEqual(result, ())
        self.assertIsInstance(result, tuple)

    def test_reannounces_monster_as_drop_after_a_recompose_would_have_run(
            self):
        drops = self._drop_monster_a()
        # The hit-on-a-different-monster recompose fires here, in the real
        # dispatch order: composed first (proven blind to the floor above),
        # THEN the companion.
        record = recompose.recompose_frames(
            self.legacy, self.anchor, self.register, ledger=self.ledger)
        self.assertEqual(record.state, recompose.STATE_COMPOSED)
        actions = recompose.ground_companion_actions(self.cell, self.legacy)
        self.assertGreater(len(actions), 0)
        for label, pc, frame, _hold in actions:
            self.assertEqual(label, mob_drop_presence.ACTION_LABEL)
            self.assertEqual(frame, self.legacy.frame_pc(pc))
        # And the row is genuinely still on the ground afterwards -- the
        # companion only RESENDS, it never claims or expires anything.
        taken = self.cell.take(drops[0].drop_key)
        self.assertEqual(taken.drop_key, drops[0].drop_key)

    def test_matches_the_shipped_mechanism_exactly_not_a_second_encoder(
            self):
        self._drop_monster_a()
        got = recompose.ground_companion_actions(self.cell, self.legacy)
        expected = mob_drop_presence.loot_actions(
            mob_drop_presence.sustain_a_kill(self.cell, self.legacy, ()))
        self.assertEqual(got, expected)

    def test_never_raises_on_something_that_is_not_a_cell(self):
        self.assertEqual(
            recompose.ground_companion_actions(None, self.legacy), ())
        self.assertEqual(
            recompose.ground_companion_actions("not a cell", self.legacy),
            ())

    def test_a_cell_with_no_scene_returns_an_empty_tuple(self):
        cell = mob_loot.DropLedgerCell(clock=self.clock)
        self.assertEqual(
            recompose.ground_companion_actions(cell, self.legacy), ())

    def test_the_console_line_does_not_claim_to_be_the_second_pwd_reannounce(
            self):
        # G-OBS: a token must name what actually happened.  This call site
        # is a combat hit, not a CheckSecondPwdVital reply, so it must never
        # print reannounce_ground's own cause-specific token.
        self._drop_monster_a()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            recompose.ground_companion_actions(self.cell, self.legacy)
        out = buf.getvalue()
        self.assertNotIn(mob_drop_presence.GROUND_REANNOUNCE_TOKEN, out)
        self.assertIn(mob_drop_presence.CONSOLE_TOKEN, out)

    def test_the_console_line_is_printed_even_for_a_bare_floor(self):
        # mob_drop_presence.describe_presence prints an explicit items=0
        # line for a checked-and-bare floor -- silence would be
        # indistinguishable from "this build has no call site yet".
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            recompose.ground_companion_actions(self.cell, self.legacy)
        out = buf.getvalue()
        self.assertIn(mob_drop_presence.CONSOLE_TOKEN, out)
        self.assertIn("live=0", out)


class WiringAskTests(unittest.TestCase):
    """The pasteable ask itself, and an honest, self-updating statement of
    whether runtime.py has taken it yet."""

    def test_the_wiring_ask_names_the_function_and_the_call_site(self):
        wiring = recompose.GROUND_COMPANION_WIRING
        self.assertIn("ground_companion_actions", wiring)
        self.assertIn("mob_loot_cell", wiring)
        self.assertIn("MOB_COMBAT_BAR", wiring)
        # cp874-encodable, not ASCII-only: this project's own console is
        # cp874 (Thai), and the gate's tripwire scope is cp874, not ASCII.
        wiring.encode("cp874")

    def test_runtime_py_does_not_call_it_yet(self):
        """HONEST STATE, RE-DERIVED FROM SOURCE, NOT ASSERTED IN PROSE.

        This is the mirror image of
        ``tests/test_mob_drop_presence.py``'s
        ``test_the_wiring_ask_is_fulfilled_re_derived_from_runtime_py``: that
        one proves a wiring ask WAS taken; this one proves this one has NOT
        been, so nobody can claim "WIRED" for this fix without this test
        having to be updated first (this lane's own rule: WIRED means
        observed, not named).  The day ``runtime.py`` adds the call this
        test should be flipped to assert the opposite, in the same PR that
        adds it.
        """
        import ast

        source = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        called = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None) or getattr(
                node.func, "id", None)
            if name:
                called.add(name)
        self.assertNotIn(
            "ground_companion_actions", called,
            "runtime.py now calls ground_companion_actions -- this test "
            "should be flipped to assert that (and the CORE-REQUEST in the "
            "PR that did it marked fulfilled), not left failing")


if __name__ == "__main__":
    unittest.main()
