"""LANE-A: the login door is a RULE about the registry, not a list in code.

PANYA-DECISION 20260908_1218 is a permanent rule in the owner's own words: a
character logs back in at the exact point it logged out from, in EVERY scene,
mid-ocean and island included.  Round ``9lv3fa`` implemented it by lifting the
last four ``login_entry_allowed: false`` pins (17, 126, 304, 305) and the last
two ``persist_position_allowed: false`` pins (14, 17).

WHY THIS FILE EXISTS RATHER THAN A CONSTANT LISTING THOSE SIX SCENE IDS.  A
list of the scenes that were fixed today pins the past.  What 1218 asks for is
a property of the registry FOREVER AFTER, and the only way to state it so that
it still holds for a destination nobody has written yet is to walk the whole
registry every run:

    every pinned destination that has a spawn is admissible at login AND has
    its position written back.

That sentence is the rule.  A future round that pins a new scene ``false``
while giving it a spawn - which is exactly the shape the four lifted scenes
had, and exactly the shape that stranded a character for twelve days - turns
this file red without anybody remembering to add its id anywhere.

WHAT THIS FILE DELIBERATELY DOES NOT ASSERT.  It does not assert that the
refusal mechanism is gone; 1218 keeps it, for a destination added later
WITHOUT a measured spawn.  ``test_the_refusal_still_bites_a_scene_with_no_
spawn`` and ``test_a_pinned_false_is_still_refused`` are here to prove the
fence is live on a synthetic registry, so that "no scene is shut today" can
never be read as "nothing can be shut".
"""

import dataclasses
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_entry
from pirateforce_foundation import world_scene_travel
from pirateforce_foundation.gm.warp_scene_persist import login_would_accept
from pirateforce_foundation.model import Position


# The four doors PANYA-DECISION 20260908_1218 named, and the two write pins
# that had to go with them for the decree to mean anything.  Named here as
# EXPECTATIONS ABOUT HISTORY - "these are the ones that were shut" - not as
# the set the rule is about; the rule is the registry walk below.
DOORS_LIFTED_BY_1218 = (17, 126, 304, 305)
WRITE_PINS_LIFTED_BY_1218 = (14, 17)


def _spawn_position(destination) -> Position:
    """The stored row a character standing on this scene's spawn would have.

    Built from the registry's own pinned spawn rather than from a literal, so
    a round that moves an arrival point does not have to remember this file.
    """
    x, y, z = destination.spawn
    scene_id, scene_seq = world_scene_travel.entry_fields(destination)
    return Position(scene_id, scene_seq, x, y, z)


class TheRuleOverTheWholeRegistry(unittest.TestCase):
    """The 1218 property, walked over every destination that is pinned."""

    def setUp(self):
        self.registry = world_scene_travel.load_scene_registry()
        self.destinations = list(self.registry.destinations)
        self.assertGreater(
            len(self.destinations), 1,
            "a registry that loaded as one row or none would make every "
            "assertion in this file pass without measuring anything")

    def test_every_pinned_scene_with_a_spawn_is_open_at_login(self):
        shut = [
            d.n_id for d in self.destinations
            if d.spawn is not None and not d.login_entry_allowed
        ]
        self.assertEqual(
            shut, [],
            "PANYA-DECISION 20260908_1218: a character logs back in where it "
            "logged out, in every scene. A destination that has a spawn (so a "
            "character can stand on it) but is pinned login_entry_allowed: "
            "false is a character that cannot get back into its own save. If "
            "a new scene needs to be kept out of the login path, it must be "
            "kept out of this registry until it has a measured spawn - that "
            "is the ordering 1218 asks for, and this is where it is enforced.")

    def test_every_pinned_scene_with_a_spawn_has_its_position_written(self):
        unwritten = [
            d.n_id for d in self.destinations
            if d.spawn is not None
            and not world_scene_travel.is_position_persist_allowed(
                d.n_id, self.registry)
        ]
        self.assertEqual(
            unwritten, [],
            "the other half of 1218: an open door is worth nothing if the "
            "position behind it is never written back. A scene a character "
            "may log in to but whose position is never persisted sends that "
            "character to wherever it last stood SOMEWHERE ELSE, which is the "
            "same lockout wearing a different hat.")

    def test_a_stored_row_at_every_spawn_resolves_through_the_login_path(self):
        """The rule, exercised rather than read off the pins.

        Both assertions above read flags.  This one makes the call the boot
        makes - ``resolve_entry`` with ``via_login=True``, the default the
        chief's login path takes - so a refusal added anywhere else on that
        path (no spawn, out of range, an unpinned row) fails this file too.
        """
        for destination in self.destinations:
            if destination.spawn is None:
                continue
            with self.subTest(scene=destination.n_id):
                entry = world_scene_entry.resolve_entry(
                    _spawn_position(destination),
                    registry=self.registry,
                    emit=lambda line: None,
                    via_login=True,
                )
                self.assertEqual(entry.destination.n_id, destination.n_id)

    def test_the_four_doors_1218_named_are_the_ones_that_opened(self):
        """History, pinned separately from the rule.

        If a later round satisfies the walk above by DELETING scenes 17, 126,
        304 or 305 from the registry, the rule stays green and the decree is
        still broken. This is the assertion that notices.
        """
        for n_id in DOORS_LIFTED_BY_1218:
            with self.subTest(scene=n_id):
                self.assertIn(n_id, self.registry.ids)
                self.assertTrue(self.registry[n_id].login_entry_allowed)
                self.assertTrue(login_would_accept(n_id))

    def test_the_two_write_pins_1218_needed_are_lifted(self):
        for n_id in WRITE_PINS_LIFTED_BY_1218:
            with self.subTest(scene=n_id):
                self.assertIn(n_id, self.registry.ids)
                self.assertTrue(
                    world_scene_travel.is_position_persist_allowed(
                        n_id, self.registry))


class TheFenceIsStillLive(unittest.TestCase):
    """1218 empties the set; it does not remove the ability to refuse.

    Without this class the file above would be satisfied by a build in which
    ``login_entry_allowed`` was deleted from the loader entirely, which is the
    one change that would make every scene open and every future scene open
    too - the opposite of what the decree asks for.
    """

    def _a_real_scene_that_is_not_home(self):
        """A pinned destination with a spawn, so the refusal under test is the
        only thing that can refuse it.

        Home is skipped as the SUBJECT because ``resolve_entry`` short-circuits
        several checks for it; it would prove nothing about the fence.
        """
        registry = world_scene_travel.load_scene_registry()
        for destination in registry.destinations:
            if (destination.n_id != world_scene_travel.HOME_SCENE_ID
                    and destination.spawn is not None):
                return destination
        raise AssertionError(
            "the registry has no non-home destination with a spawn, so this "
            "file cannot prove the fence bites anything")

    def test_a_pinned_false_is_still_refused_at_login(self):
        shut = dataclasses.replace(
            self._a_real_scene_that_is_not_home(), login_entry_allowed=False)
        registry = world_scene_travel.SceneRegistry(destinations=(shut,))
        with self.assertRaises(world_scene_entry.SceneEntryRefused) as caught:
            world_scene_entry.resolve_entry(
                _spawn_position(shut),
                registry=registry,
                emit=lambda line: None,
                via_login=True,
            )
        self.assertEqual(
            caught.exception.reason,
            world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN)

    def test_the_same_shut_scene_resolves_for_a_non_login_caller(self):
        """The refusal is about WHO is asking, not about the destination.

        Without this, ``login_entry_allowed`` could be reimplemented as a flat
        "this scene is unusable" and the test above would not notice.
        """
        shut = dataclasses.replace(
            self._a_real_scene_that_is_not_home(), login_entry_allowed=False)
        registry = world_scene_travel.SceneRegistry(destinations=(shut,))
        entry = world_scene_entry.resolve_entry(
            _spawn_position(shut),
            registry=registry,
            emit=lambda line: None,
            via_login=False,
        )
        self.assertEqual(entry.destination.n_id, shut.n_id)

    def test_a_pinned_false_still_stops_the_position_write(self):
        shut = dataclasses.replace(
            self._a_real_scene_that_is_not_home(),
            persist_position_allowed=False)
        registry = world_scene_travel.SceneRegistry(destinations=(shut,))
        self.assertFalse(
            world_scene_travel.is_position_persist_allowed(
                shut.n_id, registry))


if __name__ == "__main__":
    unittest.main()
