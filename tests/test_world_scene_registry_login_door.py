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

    every destination this project actually populates for a client is
    admissible at login AND has its position written back.

That sentence is the rule.  A future round that pins a new scene ``false``
while shipping a population for it - which is exactly the shape the four
lifted scenes had, and exactly the shape that stranded a character for twelve
days - turns this file red without anybody remembering to add its id
anywhere.

WHY "POPULATES" AND NOT "HAS A SPAWN" (pf-adversary D7, round ``1v5i3h``).
This file used to say "has a spawn", and that made *this test file* the thing
that forced a login door open, for two scenes 1218 never spoke about:

    997  a ``FilmScene`` this project has never sent to any client
    278  ``world_scene_travel.TEST_STAGE_SCENE_ID``, the test arena

Both carry a spawn, so the old sentence demanded a login door for both, and
"has a spawn" quietly became the house rule for who gets one.  It is not the
house rule and it was never measured; ``1218`` is about scenes a character
can log OUT of, and the honest register of those in this tree is
``world_scene_travel.CENSUS_SOURCES`` - the table that decides who is
standing in a scene when a client arrives.  The rule is now stated over that
table, and the two scenes outside it are named, counted and pinned by
``test_the_scenes_outside_the_populated_rule_are_exactly_two`` below rather
than swept into the rule.  NOTHING ABOUT THE SHIPPED REGISTRY CHANGES IN THIS
ROUND: 997 and 278 keep the doors they have today.  Whether a scene no client
is ever shown should hold a login door at all is an owner question, and it is
out this round as an ASK-COO letter; this file stops pre-deciding it.

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

    def test_every_populated_scene_is_open_at_login(self):
        shut = [
            d.n_id for d in self.destinations
            if d.n_id in world_scene_travel.CENSUS_SOURCES
            and not d.login_entry_allowed
        ]
        self.assertEqual(
            shut, [],
            "PANYA-DECISION 20260908_1218: a character logs back in where it "
            "logged out, in every scene. A destination this project ships a "
            "population for (world_scene_travel.CENSUS_SOURCES) is a scene a "
            "character can be standing in, so a login_entry_allowed: false "
            "pin on it is a character that cannot get back into its own "
            "save. If a new scene needs to be kept out of the login path, it "
            "must be kept out of CENSUS_SOURCES too - a scene with a cast "
            "and no door is the shape 1218 exists to forbid.")

    def test_the_scenes_outside_the_populated_rule_are_exactly_two(self):
        """The two the rule above does NOT speak for, named rather than swept.

        pf-adversary D7 (round ``1v5i3h``) measured the older form of this
        file forcing a login door open for both of these, on the strength of
        nothing but a spawn coordinate.  Neither is a scene a player logs out
        of: 997 is a ``FilmScene`` this project has never sent to a client,
        278 is the test arena.  Their registry rows are NOT changed by this
        round - they keep the doors 9lv3fa gave them, and see
        ``test_the_two_scenes_outside_the_rule_are_on_opposite_sides`` below
        for the ruling that has been made about 997 and NOT yet applied on
        this branch, with the measurement that says why.  The day a THIRD
        such scene appears, or the day one of these two joins the populated
        register, this case goes red and the reader has to say which side of
        the rule it belongs on instead of inheriting an answer.
        """
        outside = sorted(
            d.n_id for d in self.destinations
            if d.n_id not in world_scene_travel.CENSUS_SOURCES
        )
        self.assertEqual(
            outside, [278, 997],
            "the registry grew a scene this project populates for nobody. "
            "Decide out loud whether it is a place a character can log out "
            "of (add it to CENSUS_SOURCES, and the rule above covers it) or "
            "not (say so here, with the reason).")
        self.assertEqual(
            278, world_scene_travel.TEST_STAGE_SCENE_ID,
            "278 is named here as the test arena on the strength of "
            "TEST_STAGE_SCENE_ID, not on the strength of this file's memory")

    def test_the_two_scenes_outside_the_rule_are_on_opposite_sides(self):
        """COO-DECISION ``20260908_2055`` (option 2), condition 1: say WHY
        997 and 278 land on opposite sides, not merely that there are two.

        THE REASON IS EVIDENCE OF USE, NOT SCENE TYPE.  PANYA-DECISION
        20260908_1218 is about a character standing back up where it logged
        out.  997 is a ``FilmScene`` this project has never sent to any
        client, so no character has ever stood in it and none can have
        logged out of it; an open door there serves 1218 nowhere and lets a
        corrupt row put a player in a scene no screen renders.  278 is the
        arena an attended ticket boots into TODAY, so shutting it would take
        away something in use - the one thing CHARTER-02 says a new version
        may never do.

        🔴 WHAT THIS CASE ASSERTS IS THE TREE AS IT IS, NOT THE RULING.  The
        ruling's OWN condition 3 is that the two registry rows may ride this
        commit "only if it does not delay the M door by even one round", and
        LANE-A round 949y62 MEASURED that it does: shutting 997 turns twelve
        further cases of LANE-GM's files red on this branch, on top of the
        two already red for scene 126, and a red branch cannot be un-drafted.
        So 997 keeps its door here and the closure is a letter to COO
        (``20260909_1424_LANE-A-TO-COO-shutting-997-*``) instead of a silent skip.  278's
        half of the ruling is asserted, because nothing had to change for it.
        """
        outside = sorted(
            d.n_id for d in self.destinations
            if d.n_id not in world_scene_travel.CENSUS_SOURCES
        )
        self.assertEqual(outside, [278, 997])
        arena = world_scene_travel.destination(
            world_scene_travel.TEST_STAGE_SCENE_ID, self.registry)
        self.assertTrue(
            arena.login_entry_allowed,
            "278 is the arena an attended ticket boots into today - shutting "
            "it takes away something in use")
        self.assertTrue(
            world_scene_travel.is_position_persist_allowed(
                world_scene_travel.TEST_STAGE_SCENE_ID, self.registry),
            "a door with no writer behind it is the same lockout wearing a "
            "different hat")
        film = world_scene_travel.destination(997, self.registry)
        self.assertTrue(
            film.login_entry_allowed,
            "997's door is still open on this branch and that is DELIBERATE "
            "and reported (see this case's docstring). The day the closure "
            "lands, flip this assertion with it - a case that passes either "
            "way would be a case that measures nothing.")

    def test_every_populated_scene_has_its_position_written(self):
        unwritten = [
            d.n_id for d in self.destinations
            if d.n_id in world_scene_travel.CENSUS_SOURCES
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
            # NARROWED round `umv5w2` (pf-adversary D2 of round `sbqohw`).
            # This walk used to say `if destination.spawn is None: continue`
            # - the "a destination with a spawn is a login destination" rule
            # D7 named, left in the three cases that actually make the call
            # while only the two flag-reading cases were narrowed.  Measured
            # then: pinning 997 shut turned this file red in 2 cases, 278 in
            # 3, so an owner answering the ASK-COO letter with "997 keeps no
            # login door" could not land the answer without editing here.
            # The predicate is now the one the rest of the file uses.
            if destination.n_id not in world_scene_travel.CENSUS_SOURCES:
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
            # Same narrowing as the case above (pf-adversary D2).
            if destination.n_id not in world_scene_travel.CENSUS_SOURCES:
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

    def test_a_row_that_is_not_a_number_is_not_a_place(self):
        """pf-adversary D2 on this round's own branch, MEASURED there:
        with the third gate open, `Position(14, inf, inf, 0)` was KEPT and
        `teleport_fields` put 0000807f on the wire on every login forever,
        because no login rewrites the row any more.  NaN is worse: it loses
        every `<=` comparison silently, so it read as "outside" by luck
        rather than by decision.

        Walked over every login-openable destination, not a scene list, and
        asserted on BOTH via_login paths: a row that is not a number is not
        a place whoever is asking.
        """
        openable = [
            d for d in self.registry.destinations
            if d.login_entry_allowed
            and d.spawn is not None
            and d.n_id != world_scene_entry.HOME_SCENE_ID
        ]
        self.assertTrue(openable, "no scene is openable at login any more")
        bad = (
            (float("inf"), float("inf"), 0.0),
            (float("-inf"), 0.0, 0.0),
            (float("nan"), 0.0, 0.0),
            (0.0, float("nan"), 0.0),
            (0.0, 0.0, float("inf")),
        )
        for destination in openable:
            for x, y, z in bad:
                for via_login in (True, False):
                    with self.subTest(scene=destination.n_id, xyz=(x, y, z),
                                      via_login=via_login):
                        spawn = _spawn_position(destination)
                        entry = world_scene_entry.resolve_entry(
                            Position(spawn.scene_id, spawn.scene_seq, x, y, z),
                            registry=self.registry,
                            emit=lambda line: None,
                            via_login=via_login,
                        )
                        self.assertTrue(entry.relocated)
                        self.assertEqual(
                            entry.relocation_reason,
                            world_scene_entry.RELOCATED_ROW_NOT_FINITE)
                        self.assertEqual(
                            (entry.position.x, entry.position.y,
                             entry.position.z),
                            destination.spawn)

    def test_home_is_inside_the_not_a_place_rule_and_not_outside_it(self):
        """pf-adversary D5 of round ``sbqohw``, MEASURED here before it was
        fixed: the home arm of ``resolve_entry`` returned the row verbatim
        BEFORE the finite check ran, so scene 1 - the scene every character
        reaches by default and the only scene any character in this project
        has ever been persisted in - was the one destination the check did
        not cover.

        The case above walks every openable scene EXCEPT home and says so in
        its own filter (``d.n_id != HOME_SCENE_ID``), which is why it could
        not catch this.  This one drives home and nothing else.

        "Home keeps the row byte for byte" is a statement about WHICH
        POSITION is chosen among real places.  It was never a licence to put
        bytes the encoder refuses onto the wire, and reading it as one is
        what left this hole open.
        """
        home = world_scene_travel.destination(
            world_scene_entry.HOME_SCENE_ID, self.registry)
        self.assertIsNotNone(
            home.spawn,
            "home has no pinned spawn, so this case cannot say where a "
            "refused row should land instead")
        bad = (
            (float("inf"), 0.0, 0.0),
            (float("nan"), 0.0, 0.0),
            (0.0, float("-inf"), 0.0),
            (0.0, 0.0, float("nan")),
        )
        for x, y, z in bad:
            for via_login in (True, False):
                with self.subTest(xyz=(x, y, z), via_login=via_login):
                    lines = []
                    entry = world_scene_entry.resolve_entry(
                        Position(home.n_id, 0, x, y, z),
                        registry=self.registry,
                        emit=lines.append,
                        via_login=via_login,
                    )
                    self.assertTrue(entry.relocated)
                    self.assertEqual(
                        entry.relocation_reason,
                        world_scene_entry.RELOCATED_ROW_NOT_FINITE)
                    self.assertEqual(
                        (entry.position.x, entry.position.y, entry.position.z),
                        home.spawn)
                    # ADDED round ynfhoc (LANE-A), pf-adversary addendum on
                    # this same branch (A2): a real home relocation used to
                    # go unreported (`emit=lambda line: None` above hid it,
                    # and the home arm itself skipped the shared "second
                    # line" gate entirely).  Both are fixed now - assert the
                    # console actually says so.
                    self.assertTrue(
                        any(line.startswith("WORLD_SCENE_RELOCATED")
                            for line in lines),
                        "home relocated (row was not finite) and no "
                        "console line said so: %r" % (lines,))

    def test_a_row_the_float32_encoder_would_refuse_is_not_a_place(self):
        """pf-adversary D6 of round ``sbqohw``: being a number is not enough.

        ``3.5e38`` is finite - ``math.isfinite`` says yes - and it is OUTSIDE
        float32, so ``struct.pack("<f", ...)`` raises ``OverflowError`` in
        the encoder that puts this row on the wire.  ``OverflowError``
        subclasses ``ArithmeticError``, which none of the handlers guarding
        the login composers catches, so the thread unwinds; and the row is
        durable, so the next login does it again.

        Driven over home AND every openable destination, on both
        ``via_login`` paths, because the arm that answers this is gated on
        neither.
        """
        openable = [
            d for d in self.registry.destinations
            if d.spawn is not None
            and (d.login_entry_allowed
                 or d.n_id == world_scene_entry.HOME_SCENE_ID)
        ]
        self.assertGreater(len(openable), 1)
        too_big = 3.5e38
        bad = (
            (too_big, 0.0, 0.0),
            (-too_big, 0.0, 0.0),
            (0.0, too_big, 0.0),
            (0.0, 0.0, too_big),
        )
        for destination in openable:
            for x, y, z in bad:
                for via_login in (True, False):
                    with self.subTest(scene=destination.n_id, xyz=(x, y, z),
                                      via_login=via_login):
                        lines = []
                        entry = world_scene_entry.resolve_entry(
                            Position(destination.n_id, 0, x, y, z),
                            registry=self.registry,
                            emit=lines.append,
                            via_login=via_login,
                        )
                        self.assertTrue(entry.relocated)
                        self.assertEqual(
                            entry.relocation_reason,
                            world_scene_entry.RELOCATED_ROW_OUTSIDE_FLOAT32)
                        self.assertEqual(
                            (entry.position.x, entry.position.y,
                             entry.position.z),
                            destination.spawn)
                        # ADDED round ynfhoc (LANE-A), pf-adversary addendum
                        # on this same branch (A2): this loop includes home
                        # (see the `openable` filter above), and a relocated
                        # home row must be reported exactly like every other
                        # destination's is.
                        if destination.n_id == world_scene_entry.HOME_SCENE_ID:
                            self.assertTrue(
                                any(line.startswith("WORLD_SCENE_RELOCATED")
                                    for line in lines),
                                "home relocated (row outside float32) and "
                                "no console line said so: %r" % (lines,))

    def test_every_arrival_this_module_returns_packs_as_a_float32(self):
        """The two cases above name the two holes; this one states the
        PROPERTY they are holes in, so a third hole nobody has thought of
        turns it red without anyone remembering to add a value here.

        Asserted against ``struct.pack`` itself - the call that actually
        raises in the encoder - rather than against a range constant this
        file could get wrong in the same direction the code got it wrong.
        """
        import struct
        rows = (
            (0.0, 0.0, 0.0),
            (float("nan"), float("nan"), float("nan")),
            (float("inf"), float("-inf"), 0.0),
            (3.5e38, -3.5e38, 3.5e38),
            (1e308, 0.0, 0.0),
        )
        openable = [
            d for d in self.registry.destinations
            if d.spawn is not None
            and (d.login_entry_allowed
                 or d.n_id == world_scene_entry.HOME_SCENE_ID)
        ]
        self.assertGreater(len(openable), 1)
        for destination in openable:
            for x, y, z in rows:
                for heading in (0.0, float("nan"), 3.5e38, float("-inf")):
                    with self.subTest(scene=destination.n_id, xyz=(x, y, z),
                                      heading=heading):
                        entry = world_scene_entry.resolve_entry(
                            Position(destination.n_id, 0, x, y, z, heading),
                            registry=self.registry,
                            emit=lambda line: None,
                            via_login=True,
                        )
                        for value in (entry.position.x, entry.position.y,
                                      entry.position.z,
                                      entry.position.heading):
                            struct.pack("<f", value)

    def test_a_heading_the_encoder_refuses_is_replaced_and_reported(self):
        """The heading rides the same encoder as the coordinates.

        ``_row_is_finite`` says in its own docstring that heading is left
        alone because a wrong heading is corrected by the next client report.
        That is true of a WRONG heading and false of one the encoder cannot
        carry: NaN and ``3.5e38`` unwind the same thread, and the relocation
        arms handed ``row.heading`` straight back to ``entry_position``.

        Replaced rather than relocated - the character still lands where the
        rules put them - and the replacement is REPORTED, because a silent
        rewrite is what this module spent three rounds removing.
        """
        home = world_scene_travel.destination(
            world_scene_entry.HOME_SCENE_ID, self.registry)
        spawn = _spawn_position(home)
        for heading in (float("nan"), float("inf"), 3.5e38, -3.5e38):
            with self.subTest(heading=heading):
                lines = []
                entry = world_scene_entry.resolve_entry(
                    Position(spawn.scene_id, spawn.scene_seq,
                             spawn.x, spawn.y, spawn.z, heading),
                    registry=self.registry,
                    emit=lines.append,
                    via_login=True,
                )
                self.assertEqual(entry.position.heading, 0.0)
                self.assertTrue(
                    any(line.startswith("SCENE_ENTRY_HEADING_REPLACED")
                        for line in lines),
                    "the heading was rewritten and the console did not say "
                    "so: %r" % (lines,))
        # And a heading the encoder CAN carry is untouched and unreported,
        # or this case would pass on a module that replaced every heading.
        lines = []
        entry = world_scene_entry.resolve_entry(
            Position(spawn.scene_id, spawn.scene_seq,
                     spawn.x, spawn.y, spawn.z, 1.75),
            registry=self.registry,
            emit=lines.append,
            via_login=True,
        )
        self.assertEqual(entry.position.heading, 1.75)
        self.assertFalse(
            any(line.startswith("SCENE_ENTRY_HEADING_REPLACED")
                for line in lines))

    def test_the_measured_envelope_is_pinned_from_BOTH_sides(self):
        """pf-adversary D7 of round ``sbqohw``, MEASURED: the envelope in
        ``_measured_envelope_refutes`` could be widened ~550x and the whole
        suite stayed green.  Every case that touched it drove a row far
        outside the box, so only the LOWER bound of the envelope was pinned;
        nothing said how generous it is allowed to be.

        The doubling (``extent`` - a full box width - used as a RADIUS) is a
        CHOICE and the module says so.  A choice nothing measures is a
        choice the next round can change by accident, so this case pins it
        from both sides at once: one row just inside the envelope must be
        kept, one row just outside it must be thrown away.  Widening turns
        the second red; tightening turns the first red.

        Derived from the registry's own ground block, not from literals, so
        a round that re-measures a scene does not have to remember this file
        - only a round that changes the RULE does, which is the point.
        """
        with_ground = [
            d for d in self.registry.destinations
            if d.ground_extent is not None and d.ground_box is not None
            and d.login_entry_allowed
        ]
        self.assertTrue(
            with_ground,
            "no destination carries a measured ground box any more, so this "
            "case would pass without measuring the envelope at all")
        for destination in with_ground:
            x_min, x_max, y_min, y_max = destination.ground_box
            extent_x, extent_y = destination.ground_extent
            # THE TWO ENVELOPES ARE CENTRED ON DIFFERENT POINTS AND THIS
            # CASE MUST NOT CONFLATE THEM (it did on its first run, and
            # scene 278 said so): `_ground_evidence` centres the radius on
            # the pinned SPAWN, and `_measured_envelope_refutes` - the arm
            # for a scene whose spawn is a PROVISIONAL-OWNER-DECREE, where
            # that spawn is not a measured point to centre anything on -
            # centres it on the BOX.  Same radius, different centre.
            decreed = (
                destination.spawn_provenance is not None
                and destination.spawn_provenance.startswith(
                    "PROVISIONAL-OWNER-DECREE")
            )
            if decreed:
                centre_x = (x_min + x_max) / 2.0
                centre_y = (y_min + y_max) / 2.0
            else:
                centre_x, centre_y, _z = destination.spawn
            margin = 1.0
            _, scene_seq = world_scene_travel.entry_fields(destination)
            inside = Position(
                destination.n_id, scene_seq,
                centre_x + extent_x - margin, centre_y, 0.0)
            outside = Position(
                destination.n_id, scene_seq,
                centre_x + extent_x + margin, centre_y, 0.0)
            with self.subTest(scene=destination.n_id, side="inside"):
                entry = world_scene_entry.resolve_entry(
                    inside, registry=self.registry,
                    emit=lambda line: None, via_login=True)
                self.assertFalse(
                    entry.relocated,
                    "a row %.3f units from the box centre, inside the "
                    "envelope this module declares, was thrown away - the "
                    "envelope has been TIGHTENED" % (extent_x - margin,))
            with self.subTest(scene=destination.n_id, side="outside"):
                entry = world_scene_entry.resolve_entry(
                    outside, registry=self.registry,
                    emit=lambda line: None, via_login=True)
                self.assertTrue(
                    entry.relocated,
                    "a row %.3f units from the box centre, OUTSIDE the "
                    "envelope this module declares, was kept - the envelope "
                    "has been WIDENED, which is the direction nothing in "
                    "this suite used to measure" % (extent_x + margin,))
            with self.subTest(scene=destination.n_id, side="y"):
                self.assertTrue(
                    world_scene_entry.resolve_entry(
                        Position(destination.n_id, scene_seq,
                                 centre_x, centre_y + extent_y + margin, 0.0),
                        registry=self.registry,
                        emit=lambda line: None, via_login=True).relocated,
                    "the y half of the envelope is not pinned from above")
            # ADDED round ynfhoc (LANE-A), pf-adversary addendum on this same
            # branch (A3): every case above drives ONLY the positive side of
            # each axis (`centre + extent`).  `_measured_envelope_refutes`
            # compares with `abs(x - centre) <= extent_x`, and a mutant that
            # drops both `abs()` calls survives the whole suite unnoticed,
            # because the resulting one-sided `(x - centre) <= extent_x`
            # comparison still reads TRUE ("inside") for any large NEGATIVE
            # offset - a row on the negative side, however far outside the
            # box, would be silently KEPT under that mutant instead of
            # relocated.  These two subtests drive `centre - extent - margin`
            # (negative x, just outside) and `centre_y - extent_y - margin`
            # (negative y, just outside) and require the row be refuted, so
            # dropping either `abs()` turns one of them red.
            with self.subTest(scene=destination.n_id, side="x_negative"):
                self.assertTrue(
                    world_scene_entry.resolve_entry(
                        Position(destination.n_id, scene_seq,
                                 centre_x - extent_x - margin, centre_y, 0.0),
                        registry=self.registry,
                        emit=lambda line: None, via_login=True).relocated,
                    "a row %.3f units below the box centre on x, OUTSIDE the "
                    "envelope this module declares, was kept - the negative "
                    "side of the x envelope is not pinned"
                    % (extent_x + margin,))
            with self.subTest(scene=destination.n_id, side="y_negative"):
                self.assertTrue(
                    world_scene_entry.resolve_entry(
                        Position(destination.n_id, scene_seq,
                                 centre_x, centre_y - extent_y - margin, 0.0),
                        registry=self.registry,
                        emit=lambda line: None, via_login=True).relocated,
                    "a row %.3f units below the box centre on y, OUTSIDE the "
                    "envelope this module declares, was kept - the negative "
                    "side of the y envelope is not pinned"
                    % (extent_y + margin,))

    def test_a_kept_row_carries_the_destinations_scene_seq_not_the_rows(self):
        """pf-adversary D8 of round ``sbqohw``: the kept arms build their
        ``Position`` with ``scene_seq`` from ``entry_fields(target)`` and
        nothing anywhere asserted it, so a mutant that handed back
        ``row.scene_seq`` survived the suite.  ``scene_seq`` goes on the
        wire beside the scene id; a kept row that carries the sequence it
        happened to be stored with is a row in a frame that is not this
        scene's.

        Driven with a row whose stored ``scene_seq`` is deliberately WRONG,
        on the arm that keeps the coordinates, so the assertion is about the
        frame and not about the position.
        """
        kept_any = False
        for destination in self.destinations:
            if destination.n_id not in world_scene_travel.CENSUS_SOURCES:
                continue
            if destination.n_id == world_scene_entry.HOME_SCENE_ID:
                continue
            spawn = _spawn_position(destination)
            _, expected_seq = world_scene_travel.entry_fields(destination)
            wrong_seq = expected_seq + 7
            with self.subTest(scene=destination.n_id):
                entry = world_scene_entry.resolve_entry(
                    Position(spawn.scene_id, wrong_seq,
                             spawn.x + 50.0, spawn.y + 50.0, spawn.z),
                    registry=self.registry,
                    emit=lambda line: None,
                    via_login=True,
                )
                self.assertFalse(entry.relocated)
                self.assertEqual(
                    entry.position.scene_seq, expected_seq,
                    "a kept row carried the sequence it was STORED with "
                    "(%d) instead of the one this destination declares (%d)"
                    % (entry.position.scene_seq, expected_seq))
                kept_any = True
        self.assertTrue(
            kept_any,
            "no destination took the kept arm, so this case proved nothing")

    def test_every_kept_row_basis_is_one_this_module_declares(self):
        """pf-adversary D8 of round ioz8fd: ``KEPT_ROW_BASES`` had NO reader
        anywhere in the tree - not production, not a test - so it was a
        tuple that could drift from the strings actually printed without
        anything noticing, which is the exact failure mode it was written to
        prevent.  This is its reader: walk every login-openable destination,
        keep a row in each, and require the basis on the console to be one of
        the declared values.  A new branch that invents a fourth string, or a
        token withdrawn from the tuple but not from the code, goes red here.
        """
        seen = set()
        openable = [
            d for d in self.registry.destinations
            if d.login_entry_allowed
            and d.spawn is not None
            and d.n_id != world_scene_entry.HOME_SCENE_ID
        ]
        self.assertTrue(openable, "no scene is openable at login any more")
        for destination in openable:
            with self.subTest(scene=destination.n_id):
                spawn = _spawn_position(destination)
                stored = Position(spawn.scene_id, spawn.scene_seq,
                                  spawn.x + 20.0, spawn.y + 7.0, spawn.z)
                lines = []
                entry = world_scene_entry.resolve_entry(
                    stored, registry=self.registry, emit=lines.append,
                    via_login=True)
                if entry.relocated:
                    continue
                kept = [ln for ln in lines if "WORLD_SCENE_KEPT_ROW" in ln]
                self.assertEqual(len(kept), 1, lines)
                basis = kept[0].rsplit("basis=", 1)[1].strip()
                self.assertIn(basis, world_scene_entry.KEPT_ROW_BASES)
                seen.add(basis)
        self.assertTrue(
            seen, "every openable destination relocated its row: this case "
            "measured nothing")

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
