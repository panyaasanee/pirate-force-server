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

    def test_a_row_that_is_not_the_spawn_arrives_on_itself(self):
        """THE THIRD GATE, and the case that was missing when D1 got through.

        pf-adversary D2 of round 3a11a0, MEASURED: every case in this class
        drove a row sitting exactly ON the pinned spawn, so a mutant that
        threw the stored coordinates away and returned the spawn survived
        all of them - which is precisely the defect D1 then found in
        production code.  This case offsets the row first, so "the arrival
        equals the stored point" is asserted rather than assumed.

        The offset is small on purpose: for the one destination that has
        MEASURED ground (278) it stays inside that ground, so this case
        measures the third gate and not the ground test.  The ground test
        keeps its own case below.
        """
        offset = 50.0
        kept = 0
        for destination in self.destinations:
            if destination.spawn is None:
                continue
            with self.subTest(scene=destination.n_id):
                spawn = _spawn_position(destination)
                stored = Position(
                    spawn.scene_id, spawn.scene_seq,
                    spawn.x + offset, spawn.y + offset, spawn.z,
                )
                entry = world_scene_entry.resolve_entry(
                    stored,
                    registry=self.registry,
                    emit=lambda line: None,
                    via_login=True,
                )
                if destination.n_id == world_scene_entry.HOME_SCENE_ID:
                    # Home is the one scene that never went through the
                    # ground test at all; it keeps the row byte for byte and
                    # is not evidence about the gate this case is here for.
                    self.assertEqual(
                        (entry.position.x, entry.position.y, entry.position.z),
                        (stored.x, stored.y, stored.z))
                    continue
                self.assertEqual(
                    (entry.position.x, entry.position.y, entry.position.z),
                    (stored.x, stored.y, stored.z),
                    "PANYA-DECISION 20260908_1218: logging in returns a "
                    "character to the point it logged out from. Scene %d "
                    "moved it to %r instead - the third gate "
                    "(world_scene_entry._ground_refutes_stored_row) is the "
                    "one that decides this, and an open door plus a written "
                    "row does not imply it."
                    % (destination.n_id,
                       (entry.position.x, entry.position.y, entry.position.z)))
                self.assertFalse(entry.relocated)
                self.assertIsNone(entry.relocation_reason)
                kept += 1
        self.assertGreater(
            kept, 1,
            "this case must have driven more than one non-home destination "
            "or it proves nothing about the registry")

    def test_measured_ground_still_refuses_a_row_it_can_see_is_outside(self):
        """The narrowing is a narrowing, not a removal of the ground test.

        Round ioz8fd stopped a MISSING ground block and the
        PROVISIONAL-OWNER-DECREE veto from throwing a stored row away, on
        the grounds that neither is a measurement.  A row that a real,
        spawn-centred extent puts outside itself is a measurement, and it
        must still relocate - otherwise the change deleted the fence
        instead of narrowing it.  Driven over whichever rows actually carry
        that evidence rather than a scene id, so this case does not go red
        the day one is added or removed; it asserts there is at least one.
        """
        measured = [
            d for d in self.destinations
            if d.spawn is not None
            and d.ground_extent is not None
            and not (d.spawn_provenance or "").startswith(
                "PROVISIONAL-OWNER-DECREE")
        ]
        self.assertTrue(
            measured,
            "no destination carries spawn-centred ground evidence any more, "
            "so nothing in this tree can refuse a stored row and this case "
            "would pass by measuring an empty list")
        for destination in measured:
            with self.subTest(scene=destination.n_id):
                spawn = _spawn_position(destination)
                extent_x, extent_y = destination.ground_extent
                stored = Position(
                    spawn.scene_id, spawn.scene_seq,
                    spawn.x + extent_x * 10.0,
                    spawn.y + extent_y * 10.0,
                    spawn.z,
                )
                entry = world_scene_entry.resolve_entry(
                    stored,
                    registry=self.registry,
                    emit=lambda line: None,
                    via_login=True,
                )
                self.assertTrue(entry.relocated)
                self.assertEqual(
                    entry.relocation_reason,
                    world_scene_entry.RELOCATED_OUTSIDE_GROUND)
                self.assertEqual(
                    (entry.position.x, entry.position.y, entry.position.z),
                    destination.spawn)

    def test_the_console_says_which_rule_kept_the_row(self):
        """An attended tester reads the console, not `entry.relocated`.

        Two different rules keep a row - measured ground reached it, or
        nothing measured refutes it - and before round ioz8fd the line was
        identical either way, so a tester could not tell a coordinate this
        project has evidence for from one it has only the player's word
        for.  COO-DECISION 20260904_1646 item 2 is the standing rule.

        REWRITTEN ROUND 1v5i3h, pf-adversary D2 of round ioz8fd: the version
        this replaces asserted ``basis=login_row_not_refuted_by_measured_
        ground`` on THIS scene, and that string was false here.  Scene 17
        carries a measured placement box; the row below is inside it; the
        console now says which of the two it is, and the case that scene 17
        HAS a measurement is pinned right beside the assertion so this can
        never again go green by measuring a scene that has none.
        """
        sea = 17
        destination = self.registry[sea]
        self.assertIsNotNone(
            destination.ground_box,
            "scene 17 lost its measured placement box: this case now proves "
            "the wrong sentence, and _measured_envelope_refutes has nothing "
            "left to refute a garbage row with")
        spawn = _spawn_position(destination)
        stored = Position(spawn.scene_id, spawn.scene_seq,
                          spawn.x - 149.0, spawn.y - 1250.3, 745.0)
        lines = []
        entry = world_scene_entry.resolve_entry(
            stored, registry=self.registry, emit=lines.append, via_login=True)
        kept_lines = [ln for ln in lines if "WORLD_SCENE_KEPT_ROW" in ln]
        self.assertEqual(len(kept_lines), 1, lines)
        self.assertIn(
            "basis=%s" % world_scene_entry.KEPT_ROW_INSIDE_ENVELOPE,
            kept_lines[0])
        self.assertEqual(entry.position.x, stored.x)
        self.assertEqual(entry.position.y, stored.y)

    def test_a_scene_with_no_ground_block_says_so_instead_of_claiming_one(self):
        """The other half of the token D2 split in two.

        Scenes 14, 126, 304 and 305 have no ``ground`` block at all, so the
        honest sentence about their kept rows is "there is nothing measured
        here", which is a different fact from scene 17's "there is, and this
        row is inside it".  Driven off the PROPERTY (no ground block) rather
        than a list of scene ids, with a guard so an empty list cannot pass.
        """
        unmeasured = [
            d for d in self.registry.destinations
            if d.login_entry_allowed
            and d.ground_extent is None
            and d.spawn is not None
            and d.n_id != world_scene_entry.HOME_SCENE_ID
        ]
        self.assertTrue(unmeasured, "no login scene lacks a ground block")
        for destination in unmeasured:
            with self.subTest(scene=destination.n_id):
                spawn = _spawn_position(destination)
                stored = Position(spawn.scene_id, spawn.scene_seq,
                                  spawn.x + 50.0, spawn.y + 18.0, spawn.z)
                lines = []
                world_scene_entry.resolve_entry(
                    stored, registry=self.registry, emit=lines.append,
                    via_login=True)
                kept = [ln for ln in lines if "WORLD_SCENE_KEPT_ROW" in ln]
                self.assertEqual(len(kept), 1, lines)
                self.assertIn(
                    "basis=%s" % world_scene_entry.KEPT_ROW_NO_MEASUREMENT,
                    kept[0])

    def test_the_measured_box_refutes_a_row_the_decree_veto_could_not(self):
        """pf-adversary D2 of round ioz8fd, the defect itself.

        Scene 17 has a decreed spawn AND a measured placement box.  The
        radius test is centred on the spawn, so the decree veto disqualifies
        it - correctly - and round ioz8fd then read that veto as "nothing
        measured refutes this row" and kept a stored row of
        (999999, 999999, 999999) at sea.  The box was three fields away in
        the same JSON object the whole time.
        """
        destination = self.registry[17]
        self.assertTrue(
            (destination.spawn_provenance or "").startswith(
                "PROVISIONAL-OWNER-DECREE"),
            "scene 17's spawn is no longer decreed, so this case is no "
            "longer exercising the veto path it was written for")
        spawn = _spawn_position(destination)
        stored = Position(spawn.scene_id, spawn.scene_seq,
                          999999.0, 999999.0, 999999.0)
        entry = world_scene_entry.resolve_entry(
            stored, registry=self.registry, emit=lambda line: None,
            via_login=True)
        self.assertTrue(entry.relocated)
        self.assertEqual(
            entry.relocation_reason,
            world_scene_entry.RELOCATED_OUTSIDE_GROUND)
        self.assertEqual(
            (entry.position.x, entry.position.y, entry.position.z),
            destination.spawn)

    def test_the_decree_token_says_whether_the_row_or_the_pin_put_it_there(self):
        """pf-adversary D1 of round ioz8fd: two arrivals, identical bytes.

        A durable row of (17, 0,0,0) is kept - it is inside the envelope and
        it moves nothing - and it happens to equal the decreed point, so the
        second console line is correctly not printed and what a tester saw
        was a decree token indistinguishable from a real decreed arrival.
        A zero row is what an uninitialised character row looks like.
        """
        destination = self.registry[17]
        decreed = _spawn_position(destination)
        for stored, expected in (
            (Position(decreed.scene_id, decreed.scene_seq,
                      decreed.x, decreed.y, decreed.z), "from=stored_row"),
            (Position(decreed.scene_id, decreed.scene_seq,
                      999999.0, 999999.0, 999999.0), "from=pinned_spawn"),
        ):
            with self.subTest(expected=expected):
                lines = []
                world_scene_entry.resolve_entry(
                    stored, registry=self.registry, emit=lines.append,
                    via_login=True)
                token = [ln for ln in lines if ln.startswith("SCENE_ENTRY ")]
                self.assertEqual(len(token), 1, lines)
                self.assertIn(expected, token[0])

    def test_the_decree_token_does_not_fire_for_an_arrival_off_the_pin(self):
        """The gate pf-adversary D1 measured as having NO coverage at all:
        deleting ``position == target.spawn`` from the token's condition
        survived every one of the 14,775 tests in the tree.  A kept row that
        is not the decreed point must print no decree token - otherwise the
        token means "this scene has a decree" rather than "this arrival used
        it", and the owner's decision 20260827_1445 asked for the second.
        """
        destination = self.registry[17]
        spawn = _spawn_position(destination)
        stored = Position(spawn.scene_id, spawn.scene_seq,
                          spawn.x - 149.0, spawn.y - 1250.3, 745.0)
        lines = []
        entry = world_scene_entry.resolve_entry(
            stored, registry=self.registry, emit=lines.append, via_login=True)
        self.assertNotEqual(
            (entry.position.x, entry.position.y, entry.position.z),
            destination.spawn)
        self.assertEqual(
            [ln for ln in lines if ln.startswith("SCENE_ENTRY ")], [], lines)

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
