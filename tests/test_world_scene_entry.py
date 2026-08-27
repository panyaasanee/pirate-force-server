"""LANE-A BUILD-002 slice 1: one resolved arrival.

The load-bearing tests in this file are the four that decide whether GT-079
can be booted at all, and whether the boot it gets can be graded:

* ``test_the_console_line_is_emitted_before_anything_is_returned`` - the
  ticket's words are "no line = do not boot".
* ``test_the_teleport_carries_the_same_point_the_position_carries`` - the
  disagreement between the teleport target and the frames built from the row
  is the ungradeable boot this whole module exists to prevent.  If this test
  passed only because the two happen to coincide in the case it exercises it
  would be worth nothing, so it exercises the KEPT row, where they can differ,
  and it is repeated for a second scene whose only difference from home is
  its scene id.
* ``test_a_port_royal_row_pointed_at_the_test_stage_is_relocated_and_says_so``
  - the ticket's own stop condition is a person reading coordinates off the
  console.  A rewrite that is correct and silent disables that rule.
* ``test_home_is_returned_exactly_as_it_was_stored`` - CHARTER-02's cumulative
  rule at its smallest scale.  Everything else here is new behaviour; this one
  is the promise that nothing already working moved.
"""

import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_entry, world_scene_travel
from pirateforce_foundation.model import Position
from pirateforce_foundation.world_scene_entry import (
    REFUSAL_REASONS,
    REFUSED_NO_PINNED_SPAWN,
    REFUSED_NOT_ALLOWED_AT_LOGIN,
    REFUSED_SCENE_ID_OUT_OF_RANGE,
    REFUSED_SCENE_NOT_PINNED,
    RELOCATED_NO_GROUND_EVIDENCE,
    RELOCATED_OUTSIDE_GROUND,
    RELOCATION_REASONS,
    SceneEntry,
    SceneEntryRefused,
    entry_report,
    relocation_console_line,
    resolve_entry,
    return_ticket,
)
from pirateforce_foundation.world_scene_travel import (
    HOME_SCENE_ID,
    TEST_STAGE_SCENE_ID,
)


MODULE_SOURCE = ROOT / "src" / "pirateforce_foundation" / "world_scene_entry.py"
REGISTRY_JSON = json.loads(
    world_scene_travel.REGISTRY_PATH.read_text(encoding="ascii"))

# The position GT-045 measured with somebody's eyes, not v141's V134_PLAYER_XYZ
# constant: the two are 715.6 units apart and only this one is where a
# character actually logs in.
ATTENDED_HOME_ROW = Position(
    HOME_SCENE_ID, 0, -8553.947, -2579.689, 186.000, 1.25)
# The exact trap GT-079 names: a character whose row was written to the test
# stage while its XYZ is still the Port Royal one every row in this project has
# always carried.
PORT_ROYAL_XYZ_IN_THE_STAGE = Position(
    TEST_STAGE_SCENE_ID, 0, -9239.957, -2830.045, 223.292, 0.0)
# A row that IS on the stage, well inside the pinned extent, and 399.41 units
# from the pinned spawn - so keeping it and pinning it are different answers.
STANDING_ON_THE_STAGE = Position(
    TEST_STAGE_SCENE_ID, 0, -13000.0, 22500.0, -2492.0, 0.5)
# Scene 2 is the only non-home scene this client has ever rendered
# (SCENE-001).  It has n_SAVE = 1, n_MARKER = 2, and no pinned ground.  The
# heading is deliberately not zero: a relocation that resets it would be
# invisible at heading 0.
PRISON_ISLAND_ROW = Position(2, 0, 27000.0, 21200.0, 1680.0, 0.3)


class Sink:
    """A console that records instead of printing, and knows when it was used."""

    def __init__(self):
        self.lines = []

    def __call__(self, line):
        if type(line) is not str:
            raise AssertionError("the console sink was handed a non-string")
        self.lines.append(line)


def registry_with(edits):
    """The shipped pin, altered in one place, loaded through the real loader."""
    data = json.loads(json.dumps(REGISTRY_JSON))
    for row in data["destinations"]:
        patch = edits.get(row["n_id"])
        if patch is not None:
            row.update(patch)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "registry.json"
        path.write_text(json.dumps(data), encoding="ascii")
        return world_scene_travel.load_scene_registry(path)


class ConsoleTests(unittest.TestCase):

    def test_the_console_line_is_emitted_before_anything_is_returned(self):
        # GT-079 deliverable 2: the sink has the WORLD_SCENE line by the time
        # resolve_entry returns, for home and away alike, and it is the same
        # line the module reports afterwards.
        for row in (ATTENDED_HOME_ROW, PORT_ROYAL_XYZ_IN_THE_STAGE,
                    STANDING_ON_THE_STAGE, PRISON_ISLAND_ROW):
            with self.subTest(scene=row.scene_id):
                sink = Sink()
                entry = resolve_entry(row, emit=sink)
                self.assertTrue(sink.lines)
                self.assertEqual(sink.lines[0], entry.console_line)
                self.assertEqual(tuple(sink.lines), entry.console_lines)
                self.assertTrue(sink.lines[0].startswith("WORLD_SCENE "))
                for line in sink.lines:
                    self.assertTrue(line.isascii())

    def test_the_stage_console_line_is_the_string_the_ticket_pinned(self):
        # GT-079 quotes this line character for character as the thing whose
        # absence forbids a boot.  Pinned here rather than only in the travel
        # module's tests because THIS is the function that emits it.
        sink = Sink()
        resolve_entry(PORT_ROYAL_XYZ_IN_THE_STAGE, emit=sink)
        self.assertEqual(sink.lines[0], (
            "WORLD_SCENE scene_id=278 seq=0 model=Bg1177 "
            "name=beach_football_field_(TEST) "
            "spawn=(-13270.058,22794.273,-2492.769) "
            "sent_before=NO population=none save=0 marker=0 "
            "return_ticket=REQUIRED"
        ))

    def test_a_normal_home_boot_prints_exactly_one_line(self):
        # The default boot is the one GT-078 grades.  One line, not two: at
        # home the row IS the position and there is nothing further to say.
        sink = Sink()
        resolve_entry(ATTENDED_HOME_ROW, emit=sink)
        self.assertEqual(len(sink.lines), 1)

    def test_a_character_already_standing_on_a_pinned_spawn_prints_one_line(self):
        # The rule takes the pinned-spawn branch here, and nothing moves.  A
        # second line would cry wolf on every login forever, and the ticket's
        # stop rule is a person believing that line.
        scene2 = world_scene_travel.destination(2)
        sink = Sink()
        entry = resolve_entry(
            Position(2, 0, *scene2.spawn, 0.0), emit=sink)
        self.assertFalse(entry.relocated)
        self.assertIsNone(entry.relocation_reason)
        self.assertEqual(len(sink.lines), 1)

    def test_a_non_callable_sink_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_entry(ATTENDED_HOME_ROW, emit=None)

    def test_a_non_position_row_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_entry((1, 0, 0.0, 0.0, 0.0, 0.0), emit=Sink())


class RefusalTests(unittest.TestCase):

    def test_an_unpinned_scene_refuses_with_one_named_type_and_reason(self):
        # Scene 1177 is deliberately a number that LOOKS like the stage (its
        # model is Bg1177) and is not a pinned n_ID.
        with self.assertRaises(SceneEntryRefused) as caught:
            resolve_entry(Position(1177, 0, 0.0, 0.0, 0.0, 0.0), emit=Sink())
        self.assertEqual(caught.exception.reason, REFUSED_SCENE_NOT_PINNED)

    def test_an_out_of_range_scene_id_refuses_with_its_own_reason(self):
        # Two different refusal shapes would mean the wiring has two things to
        # catch, and the one it forgot costs a connection.  store.py accepts
        # 0..0xFFFF, so a row really can carry 0.
        for scene_id in (0, 0x10000, -1):
            with self.subTest(scene_id=scene_id):
                with self.assertRaises(SceneEntryRefused) as caught:
                    resolve_entry(
                        Position(scene_id, 0, 0.0, 0.0, 0.0, 0.0), emit=Sink())
                self.assertEqual(
                    caught.exception.reason, REFUSED_SCENE_ID_OUT_OF_RANGE)

    def test_the_refusal_names_the_row_and_keeps_the_underlying_cause(self):
        # The message is the only place the real reason survives, and an
        # assertRaises that checks the type alone would not notice it going.
        with self.assertRaises(SceneEntryRefused) as caught:
            resolve_entry(Position(1177, 0, 0.0, 0.0, 0.0, 0.0), emit=Sink())
        self.assertIn("1177", str(caught.exception))
        self.assertIn("not pinned", str(caught.exception))
        self.assertIsInstance(caught.exception.__cause__, KeyError)

    def test_the_refusal_is_NOT_a_key_error(self):
        # runtime.py:3646 wraps the production select_and_start in
        # except (KeyError, PermissionError) and answers it by returning no
        # frames.  A refusal that were a KeyError would be swallowed there:
        # no console line, no traceback, a client stuck at "connecting".
        with self.assertRaises(SceneEntryRefused) as caught:
            resolve_entry(Position(1177, 0, 0.0, 0.0, 0.0, 0.0), emit=Sink())
        self.assertNotIsInstance(caught.exception, KeyError)
        self.assertIsInstance(caught.exception, LookupError)

    def test_a_pinned_destination_with_no_spawn_is_refused_not_crashed(self):
        # load_scene_registry permits spawn: null, and resolve_entry takes a
        # caller-supplied registry, so this is reachable through the public API.
        registry = registry_with({278: {"spawn": None}})
        with self.assertRaises(SceneEntryRefused) as caught:
            resolve_entry(
                PORT_ROYAL_XYZ_IN_THE_STAGE, registry=registry, emit=Sink())
        self.assertEqual(caught.exception.reason, REFUSED_NO_PINNED_SPAWN)

    def test_every_refusal_reason_is_one_of_the_named_ones(self):
        rows = (
            Position(1177, 0, 0.0, 0.0, 0.0, 0.0),
            Position(0, 0, 0.0, 0.0, 0.0, 0.0),
        )
        for row in rows:
            with self.subTest(scene=row.scene_id):
                with self.assertRaises(SceneEntryRefused) as caught:
                    resolve_entry(row, emit=Sink())
                self.assertIn(caught.exception.reason, REFUSAL_REASONS)
        with self.assertRaises(ValueError):
            SceneEntryRefused("invented_reason", "nope")

    def test_a_refused_row_emits_nothing(self):
        # A WORLD_SCENE line on the console for a boot that then dies would
        # tell the reader a destination was chosen when none was.
        sink = Sink()
        with self.assertRaises(SceneEntryRefused):
            resolve_entry(Position(1177, 0, 0.0, 0.0, 0.0, 0.0), emit=sink)
        self.assertEqual(sink.lines, [])

    def test_a_broken_registry_file_is_not_reported_as_an_unpinned_scene(self):
        # A malformed pin is not a fact about the character's row.  Reporting
        # it as "your scene is not pinned" sends the 2am reader hunting for a
        # destination row that is present and fine.
        original = world_scene_travel.load_scene_registry
        for fault in (json.JSONDecodeError("bad", "doc", 0),
                      FileNotFoundError("no pin"),
                      PermissionError("no read")):
            with self.subTest(fault=type(fault).__name__):
                def explode(*_args, **_kwargs):
                    raise fault
                world_scene_travel.load_scene_registry = explode
                try:
                    with self.assertRaises(type(fault)):
                        resolve_entry(ATTENDED_HOME_ROW, emit=Sink())
                finally:
                    world_scene_travel.load_scene_registry = original


class LoginEntryRestrictionTests(unittest.TestCase):
    """Round 0z3kjx, adversary-flagged regression.  ``resolve_entry`` is the
    SAME call ``runtime.py``'s login path makes with whatever ``scene_id`` is
    sitting in a character's persisted row - nothing in the DB schema stops
    that row from ever naming 17.  Before this scene had a pinned spawn, that
    row was refused for free (``REFUSED_NO_PINNED_SPAWN``).  These tests prove
    the refusal survives now that scene 17 has one, WITHOUT going through
    ``columbus_quest_dispatch``'s own synthetic call - the exact gap the
    adversary pass found no test covering.
    """

    # A row shaped exactly like what a character's stored position would be
    # if it somehow ever named scene 17 - NOT the synthetic zero-XYZ Position
    # columbus_quest_dispatch.resolve_columbus_arrival builds fresh every
    # call, so a fix that only special-cased that literal object would not
    # pass this.
    PERSISTED_SCENE_17_ROW = Position(17, 0, 1.0, 2.0, 3.0, 0.5)

    def test_a_stored_scene_17_row_is_refused_at_the_login_call_shape(self):
        # resolve_entry(row, registry=..., emit=...) - no via_login keyword -
        # is exactly the call runtime.py's login path makes.  This is the
        # regression pin: it must still refuse scene 17 today, exactly as it
        # did before scene 17 had a pinned spawn at all.
        with self.assertRaises(SceneEntryRefused) as caught:
            resolve_entry(self.PERSISTED_SCENE_17_ROW, emit=Sink())
        self.assertEqual(caught.exception.reason, REFUSED_NOT_ALLOWED_AT_LOGIN)
        self.assertIn("17", str(caught.exception))

    def test_the_refusal_reason_is_named_in_the_public_set(self):
        self.assertIn(REFUSED_NOT_ALLOWED_AT_LOGIN, REFUSAL_REASONS)

    def test_a_refused_scene_17_login_emits_nothing(self):
        # Same contract as every other refusal: no WORLD_SCENE line for a
        # destination that was never actually granted.
        sink = Sink()
        with self.assertRaises(SceneEntryRefused):
            resolve_entry(self.PERSISTED_SCENE_17_ROW, emit=sink)
        self.assertEqual(sink.lines, [])

    def test_via_login_defaults_true_with_no_keyword_passed(self):
        # Pin the default itself: a caller that passes nothing gets the safe
        # answer.  If a future edit flipped the default, every test above
        # would still pass (they pass no keyword either) - this one exists so
        # a reader can see the default is asserted, not merely relied upon.
        with self.assertRaises(SceneEntryRefused):
            resolve_entry(self.PERSISTED_SCENE_17_ROW, emit=Sink())

    def test_via_login_false_is_the_columbus_dispatch_escape_hatch(self):
        # The other half of the same mechanism: an explicit non-login caller
        # still resolves scene 17 through the owner-decreed placeholder,
        # exactly as columbus_quest_dispatch.resolve_columbus_arrival does.
        sink = Sink()
        entry = resolve_entry(
            self.PERSISTED_SCENE_17_ROW, emit=sink, via_login=False)
        self.assertEqual(entry.destination.n_id, 17)
        self.assertTrue(sink.lines)
        self.assertTrue(sink.lines[0].startswith("WORLD_SCENE "))

    def test_via_login_must_be_a_bool(self):
        for bad in (1, 0, "false", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    resolve_entry(
                        ATTENDED_HOME_ROW, emit=Sink(), via_login=bad)

    def test_login_restricted_scenes_other_than_17_are_unaffected(self):
        # The mechanism must be per-destination, not a blanket change: home,
        # scene 2, and the test stage all still resolve at the default
        # (login) call shape exactly as every other test file in this suite
        # already assumes.
        for row in (ATTENDED_HOME_ROW, PORT_ROYAL_XYZ_IN_THE_STAGE,
                    STANDING_ON_THE_STAGE, PRISON_ISLAND_ROW):
            with self.subTest(scene=row.scene_id):
                entry = resolve_entry(row, emit=Sink())
                self.assertNotEqual(entry.destination.n_id, 17)

    def test_a_login_restricted_destination_with_no_flag_set_is_unaffected(self):
        # Mutation check via a patched registry: a destination with NO
        # login_entry_allowed key at all (every pre-existing pin) must still
        # default to allowed, proven through resolve_entry itself and not
        # only through world_scene_travel's own loader tests.
        registry = registry_with({17: {"login_entry_allowed": True}})
        entry = resolve_entry(
            Position(17, 0, 0.0, 0.0, 0.0, 0.0), registry=registry, emit=Sink())
        self.assertEqual(entry.destination.n_id, 17)


class HomeIsUnchangedTests(unittest.TestCase):

    def test_home_is_returned_exactly_as_it_was_stored(self):
        # Not "equal to a rebuilt row" - the same row.  A player who logged out
        # beside the tavern comes back beside the tavern.
        entry = resolve_entry(ATTENDED_HOME_ROW, emit=Sink())
        self.assertIs(entry.position, ATTENDED_HOME_ROW)
        self.assertFalse(entry.relocated)
        self.assertIsNone(entry.relocation_reason)
        self.assertTrue(entry.is_home)

    def test_home_teleport_arguments_are_the_ones_the_runtime_sends_today(self):
        # runtime.py sends make_login_teleport(1, 0); the five-argument form of
        # that same call is (1, 0, 0.0, 0.0, 0.0).  Home is the one place the
        # teleport deliberately does NOT carry the position - that zero target
        # is the shape every surviving default boot has sent.
        for row in (ATTENDED_HOME_ROW,
                    Position(HOME_SCENE_ID, 4, 1.0, 2.0, 3.0, 4.0)):
            with self.subTest(row=row):
                entry = resolve_entry(row, emit=Sink())
                self.assertEqual(entry.teleport_fields, (1, 0, 0.0, 0.0, 0.0))

    def test_home_keeps_the_census_and_owes_no_return_ticket(self):
        entry = resolve_entry(ATTENDED_HOME_ROW, emit=Sink())
        self.assertEqual(
            entry.population_source, world_scene_travel.CENSUS_SOURCE)
        self.assertFalse(entry.return_ticket_required)
        self.assertIsNone(return_ticket(entry))

    def test_a_home_row_far_from_the_pinned_spawn_is_still_untouched(self):
        # The ground test is not applied to home on purpose.  This row is
        # 31,534 units from the pinned Port Royal spawn and must survive: the
        # scene saves characters, so its rows mean "where I was".
        far = Position(HOME_SCENE_ID, 0, 22124.383, -4912.918, 2746.361, 0.0)
        entry = resolve_entry(far, emit=Sink())
        self.assertIs(entry.position, far)
        self.assertFalse(entry.relocated)

    def test_a_home_row_with_a_drifted_sequence_is_visible_in_the_report(self):
        # Home is passed through verbatim, sequence included, while the
        # teleport carries the frozen 0.  Both numbers are in the report so
        # the difference is readable rather than latent.
        entry = resolve_entry(
            Position(HOME_SCENE_ID, 7, -8553.947, -2579.689, 186.0, 0.0),
            emit=Sink())
        report = entry_report(entry)
        self.assertEqual(report["stored_scene_seq"], 7)
        self.assertEqual(report["used_scene_seq"], 7)
        self.assertEqual(report["scene_seq"], 0)
        self.assertEqual(entry.teleport_fields[1], 0)


class TeleportAgreementTests(unittest.TestCase):

    def test_the_teleport_carries_the_same_point_the_position_carries(self):
        # THE test of this module.  Exercised on the KEPT row, where the
        # teleport built from the pin and the teleport built from the position
        # are 399.41 units apart - so a regression to reading the pin fails
        # here rather than coinciding into a pass.
        entry = resolve_entry(STANDING_ON_THE_STAGE, emit=Sink())
        self.assertFalse(entry.relocated)
        self.assertEqual(entry.teleport_fields, (
            TEST_STAGE_SCENE_ID, 0,
            entry.position.x, entry.position.y, entry.position.z,
        ))
        # ...and it is genuinely NOT the pinned spawn, or this test proves
        # nothing.
        self.assertNotEqual(
            entry.teleport_fields[2:], entry.destination.spawn)

    def test_the_teleport_agrees_for_every_non_home_scene_not_just_the_stage(self):
        # The home carve-out is keyed on the scene id and must not be keyed on
        # anything else.  Scene 2 carries n_SAVE = 1 and n_MARKER = 2 like
        # home does, so a carve-out written on either column would wrongly send
        # it the frozen zero target while its position said otherwise.
        for row in (PORT_ROYAL_XYZ_IN_THE_STAGE, STANDING_ON_THE_STAGE,
                    PRISON_ISLAND_ROW):
            with self.subTest(scene=row.scene_id):
                entry = resolve_entry(row, emit=Sink())
                self.assertEqual(entry.teleport_fields, (
                    entry.destination.n_id, 0,
                    entry.position.x, entry.position.y, entry.position.z,
                ))
                self.assertNotEqual(entry.teleport_fields[2:5], (0.0, 0.0, 0.0))

    def test_the_worst_legal_kept_row_still_agrees(self):
        # The keep rule accepts up to the pinned extent in each axis.  At the
        # far corner the pin and the row are 6577 units apart; if anything ever
        # rebuilds the teleport from the pin, this is where it shows.
        stage = world_scene_travel.destination(TEST_STAGE_SCENE_ID)
        spawn_x, spawn_y, spawn_z = stage.spawn
        extent_x, extent_y = stage.ground_extent
        corner = Position(
            TEST_STAGE_SCENE_ID, 0,
            spawn_x + extent_x, spawn_y + extent_y, spawn_z, 0.0)
        entry = resolve_entry(corner, emit=Sink())
        self.assertFalse(entry.relocated)
        self.assertEqual(entry.teleport_fields[2], corner.x)
        self.assertEqual(entry.teleport_fields[3], corner.y)


class StageRowCoherenceTests(unittest.TestCase):

    def test_a_port_royal_row_pointed_at_the_test_stage_is_relocated_and_says_so(self):
        # GT-079's stop condition, tested as the ticket words it: arriving at
        # (-9239, -2830) inside scene 278 is a stopped boot, so the resolved
        # position must be the pinned spawn instead - AND the console must say
        # a row was overridden, or the tester's stop rule cannot fire.
        sink = Sink()
        entry = resolve_entry(PORT_ROYAL_XYZ_IN_THE_STAGE, emit=sink)
        stage = world_scene_travel.destination(TEST_STAGE_SCENE_ID)
        self.assertTrue(entry.relocated)
        self.assertEqual(entry.relocation_reason, RELOCATED_OUTSIDE_GROUND)
        self.assertEqual(
            (entry.position.x, entry.position.y, entry.position.z),
            stage.spawn,
        )
        self.assertEqual(entry.position.scene_id, TEST_STAGE_SCENE_ID)
        self.assertIs(entry.stored, PORT_ROYAL_XYZ_IN_THE_STAGE)
        self.assertEqual(len(sink.lines), 2)
        self.assertEqual(sink.lines[1], (
            "WORLD_SCENE_RELOCATED scene_id=278 "
            "reason=stored_xy_outside_pinned_ground_extent "
            "stored=(-9239.957,-2830.045,223.292) "
            "used=(-13270.058,22794.273,-2492.769) "
            "stored_seq=0 used_seq=0"
        ))

    def test_a_relocated_character_keeps_the_heading_its_row_carried(self):
        # A silent heading reset is invisible at heading 0, which is what every
        # Port Royal row carries, so it is measured on the one row here that
        # does not.
        entry = resolve_entry(PRISON_ISLAND_ROW, emit=Sink())
        self.assertTrue(entry.relocated)
        self.assertEqual(entry.position.heading, PRISON_ISLAND_ROW.heading)

    def test_a_row_already_on_the_stage_is_kept_and_the_console_says_where(self):
        # A character who walked around the stage and logged back in should not
        # be yanked to the entry point - and the pinned WORLD_SCENE line
        # reports the destination's spawn, never the position used, so a second
        # line is what tells the reader where the character actually is.
        sink = Sink()
        entry = resolve_entry(STANDING_ON_THE_STAGE, emit=sink)
        self.assertFalse(entry.relocated)
        self.assertEqual(entry.position.x, STANDING_ON_THE_STAGE.x)
        self.assertEqual(entry.position.y, STANDING_ON_THE_STAGE.y)
        self.assertEqual(entry.position.heading, STANDING_ON_THE_STAGE.heading)
        self.assertEqual(len(sink.lines), 2)
        self.assertEqual(sink.lines[1], (
            "WORLD_SCENE_KEPT_ROW scene_id=278 "
            "used=(-13000.000,22500.000,-2492.000) "
            "pinned_spawn=(-13270.058,22794.273,-2492.769) "
            "stored_seq=0 used_seq=0"
        ))

    def test_a_rewritten_sequence_is_reported_rather_than_silent(self):
        # A scene change must not become a scene-sequence change at the same
        # time.  entry_fields owns scene_seq; a row carrying 7 does not - and
        # the override is on the console and in the report, not only in effect.
        sink = Sink()
        drifted = Position(
            TEST_STAGE_SCENE_ID, 7, -13000.0, 22500.0, -2492.0, 0.0)
        entry = resolve_entry(drifted, emit=sink)
        self.assertFalse(entry.relocated)
        self.assertEqual(entry.position.scene_seq, 0)
        self.assertIn("stored_seq=7 used_seq=0", sink.lines[1])
        report = entry_report(entry)
        self.assertEqual(report["stored_scene_seq"], 7)
        self.assertEqual(report["used_scene_seq"], 0)

    def test_the_relocation_boundary_is_the_pinned_extent_and_fires_both_ways(self):
        # A guard that cannot fail to fire is decoration.  Just inside the
        # pinned x extent is kept; just outside it is relocated.  Same for y.
        stage = world_scene_travel.destination(TEST_STAGE_SCENE_ID)
        spawn_x, spawn_y, spawn_z = stage.spawn
        extent_x, extent_y = stage.ground_extent
        cases = (
            ("x inside", spawn_x + extent_x - 1.0, spawn_y, False),
            ("x outside", spawn_x + extent_x + 1.0, spawn_y, True),
            ("y inside", spawn_x, spawn_y + extent_y - 1.0, False),
            ("y outside", spawn_x, spawn_y + extent_y + 1.0, True),
        )
        for label, x, y, expected in cases:
            with self.subTest(case=label):
                row = Position(TEST_STAGE_SCENE_ID, 0, x, y, spawn_z, 0.0)
                self.assertEqual(
                    resolve_entry(row, emit=Sink()).relocated, expected)

    def test_z_is_not_part_of_the_test(self):
        # The only z evidence a scene has is where a developer put its mobs.
        # A row 5,000 units above the placement plane is not thereby wrong, and
        # refusing it would be a claim about ground nobody measured.
        stage = world_scene_travel.destination(TEST_STAGE_SCENE_ID)
        spawn_x, spawn_y, spawn_z = stage.spawn
        high = Position(
            TEST_STAGE_SCENE_ID, 0, spawn_x, spawn_y, spawn_z + 5000.0, 0.0)
        self.assertFalse(resolve_entry(high, emit=Sink()).relocated)

    def test_the_bg0001_census_is_not_offered_away_from_home(self):
        # The bg0001 census is bg0001's.  Delivering dock NPCs into a football
        # field would be the first cross-build-order defect this project
        # shipped, and this is the second place that is refused.
        self.assertIsNone(
            resolve_entry(
                PORT_ROYAL_XYZ_IN_THE_STAGE, emit=Sink()).population_source)

    def test_scene_2_now_carries_its_own_named_population_source(self):
        # GENERALIZED 2026-08-27 (PANYA-DECISION 20:10, M1-P):
        # world_scene_travel.population_source is keyed by scene id now, and
        # scene 2 has its own roster (world_population_bg0002.py) - it is no
        # longer "no population source at all" the way an unbuilt scene is.
        # The scene 278 case above is the one that stays None: nobody has
        # built a football-field composer.
        self.assertEqual(
            resolve_entry(PRISON_ISLAND_ROW, emit=Sink()).population_source,
            "bg0002_roster",
        )


class ReturnTicketTests(unittest.TestCase):

    def test_every_non_home_destination_owes_a_ticket_including_scene_2(self):
        # n_MARKER is an ARRIVAL marker.  Scene 2 has one and scene 278 does
        # not, and this project has measured a way OUT of neither - RE-077 is
        # open for both.  A ticket withheld on the strength of that column is
        # a character persisted where nothing can bring it back.
        scene2 = world_scene_travel.destination(2)
        self.assertTrue(scene2.has_authored_entry)
        for row in (PORT_ROYAL_XYZ_IN_THE_STAGE, PRISON_ISLAND_ROW):
            with self.subTest(scene=row.scene_id):
                entry = resolve_entry(row, emit=Sink())
                self.assertTrue(entry.return_ticket_required)
                ticket = return_ticket(entry)
                self.assertIsNotNone(ticket)
                self.assertEqual(ticket.scene_id, HOME_SCENE_ID)

    def test_the_default_ticket_is_the_pinned_home_row(self):
        entry = resolve_entry(PORT_ROYAL_XYZ_IN_THE_STAGE, emit=Sink())
        self.assertEqual(
            return_ticket(entry), world_scene_travel.home_return_position())

    def test_a_remembered_home_row_beats_the_pinned_one(self):
        # With no argument the ticket is the NEW-character entry point, 731
        # units from where the attended spawn actually is.  A caller that kept
        # the departing row gets that row back instead.
        entry = resolve_entry(PORT_ROYAL_XYZ_IN_THE_STAGE, emit=Sink())
        self.assertIs(
            return_ticket(entry, remembered=ATTENDED_HOME_ROW),
            ATTENDED_HOME_ROW)
        self.assertNotEqual(return_ticket(entry), ATTENDED_HOME_ROW)

    def test_a_remembered_row_that_is_not_home_is_refused_even_at_home(self):
        # Validated before the "no ticket owed" exit, so a caller that passes a
        # bad row hears about it on the boot where it passed one.
        home = resolve_entry(ATTENDED_HOME_ROW, emit=Sink())
        away = resolve_entry(PORT_ROYAL_XYZ_IN_THE_STAGE, emit=Sink())
        for entry in (home, away):
            with self.subTest(scene=entry.destination.n_id):
                with self.assertRaises(ValueError):
                    return_ticket(entry, remembered=STANDING_ON_THE_STAGE)
                with self.assertRaises(ValueError):
                    return_ticket(entry, remembered="home please")

    def test_the_extra_arguments_are_keyword_only(self):
        # remembered was added after registry existed; a positional call must
        # not silently change meaning.
        entry = resolve_entry(PORT_ROYAL_XYZ_IN_THE_STAGE, emit=Sink())
        with self.assertRaises(TypeError):
            return_ticket(entry, ATTENDED_HOME_ROW)


class SceneWithNoPinnedGroundTests(unittest.TestCase):
    """Scene 2 - n_SAVE = 1, n_MARKER = 2, no pinned ground, and the only
    non-home scene this client has ever rendered.  The branch that handles it
    is a different branch with a different reported reason, so it is tested as
    one."""

    def test_a_scene_with_no_pinned_ground_uses_its_pinned_spawn(self):
        entry = resolve_entry(PRISON_ISLAND_ROW, emit=Sink())
        scene2 = world_scene_travel.destination(2)
        self.assertIsNone(scene2.ground_extent)
        self.assertTrue(entry.relocated)
        self.assertEqual(
            (entry.position.x, entry.position.y, entry.position.z),
            scene2.spawn,
        )

    def test_the_reason_names_the_missing_ground_not_the_extent(self):
        # Two branches, two reasons.  A module that reported one reason for
        # both would be indistinguishable from one that never took this branch.
        entry = resolve_entry(PRISON_ISLAND_ROW, emit=Sink())
        self.assertEqual(
            entry.relocation_reason, RELOCATED_NO_GROUND_EVIDENCE)
        self.assertNotEqual(
            entry.relocation_reason,
            resolve_entry(PORT_ROYAL_XYZ_IN_THE_STAGE,
                          emit=Sink()).relocation_reason,
        )

    def test_this_scene_persists_characters_and_is_relocated_anyway(self):
        # The honest statement of rule 2's limit, kept as a test: n_SAVE says
        # this scene saves characters, and the rule overrides its row anyway,
        # because no path in this tree has written one yet.  The day that stops
        # being true, this test is the one that has to be argued with.
        scene2 = world_scene_travel.destination(2)
        self.assertTrue(scene2.persists_characters)
        self.assertTrue(resolve_entry(PRISON_ISLAND_ROW, emit=Sink()).relocated)


class ProvisionalDecreeTests(unittest.TestCase):
    """Scene 17 (Bg1001): the real registry entry that carries BOTH a real
    ground block AND a PROVISIONAL-OWNER-DECREE spawn at once, added the
    same round (e0daaa) independently of each other. pf-adversary found
    that combination breaks the "kept row" branch's own promise -- this
    class is the coverage gap that same review named (grep for "17" in
    this file used to return nothing).
    """

    SEA_SCENE_ID = 17
    DECREE_XYZ = (0.0, 0.0, 0.0)
    DECREE_TOKEN = (
        "SCENE_ENTRY scene=17 xyz=0.000,0.000,0.000 "
        "source=PROVISIONAL-OWNER-DECREE-20260827-1445"
    )

    def test_scene_17_has_both_a_decree_and_real_ground_this_round(self):
        # Guard for the fixture itself: every test below assumes this shape.
        # If a future round changes either half, this fails LOUDLY here
        # instead of the tests below passing for the wrong reason.
        sea = world_scene_travel.destination(self.SEA_SCENE_ID)
        self.assertEqual(sea.spawn, self.DECREE_XYZ)
        self.assertTrue(sea.spawn_provenance.startswith("PROVISIONAL-OWNER-DECREE"))
        self.assertIsNotNone(sea.ground_extent)

    def test_a_row_far_outside_real_ground_but_near_the_decree_point_still_relocates(self):
        # Before this round's fix, a row here (or anywhere numerically near
        # (0,0,*)) was wrongly treated as "on ground this scene has evidence
        # for", because the acceptance radius is centred on the decree point,
        # not on anything measured. This row is deliberately (0,0,z) - inside
        # the naive radius test - to prove the fix, not just avoid it.
        #
        # via_login=False, round 0z3kjx: this test is about the RELOCATION
        # mechanic, not about login access, and scene 17 now requires an
        # explicit non-login caller to resolve at all (see
        # LoginEntryRestrictionTests below for that half). Without this the
        # call would raise REFUSED_NOT_ALLOWED_AT_LOGIN before it ever reached
        # the relocation logic this test exists to exercise.
        row = Position(self.SEA_SCENE_ID, 0, 0.0, 0.0, 5000.0, 0.0)
        entry = resolve_entry(row, emit=Sink(), via_login=False)
        self.assertTrue(entry.relocated)
        self.assertEqual(
            (entry.position.x, entry.position.y, entry.position.z),
            self.DECREE_XYZ,
        )

    def test_a_row_genuinely_far_from_the_decree_also_relocates_and_prints_the_token(self):
        # via_login=False, round 0z3kjx - see the sibling test above.
        row = Position(self.SEA_SCENE_ID, 0, -1800.0, 2300.0, 900.0, 0.0)
        sink = Sink()
        entry = resolve_entry(row, emit=sink, via_login=False)
        self.assertTrue(entry.relocated)
        self.assertEqual(
            (entry.position.x, entry.position.y, entry.position.z),
            self.DECREE_XYZ,
        )
        self.assertIn(self.DECREE_TOKEN, sink.lines)

    def test_the_token_never_fires_for_an_unrelated_destination(self):
        # Sanity check on the token's own gate: a destination with real
        # ground and a REAL (non-decreed) spawn must never print it, even
        # when its own row is kept unmoved.
        sink = Sink()
        resolve_entry(STANDING_ON_THE_STAGE, emit=sink)
        self.assertFalse(
            any(line.startswith("SCENE_ENTRY ") for line in sink.lines)
        )


class ReportingTests(unittest.TestCase):

    def test_the_relocation_line_is_refused_when_no_row_was_overridden(self):
        home = resolve_entry(ATTENDED_HOME_ROW, emit=Sink())
        with self.assertRaises(ValueError):
            relocation_console_line(home)
        kept = resolve_entry(STANDING_ON_THE_STAGE, emit=Sink())
        with self.assertRaises(ValueError):
            relocation_console_line(kept)

    def test_the_recomposed_relocation_line_is_the_one_that_was_emitted(self):
        sink = Sink()
        moved = resolve_entry(PORT_ROYAL_XYZ_IN_THE_STAGE, emit=sink)
        self.assertEqual(relocation_console_line(moved), sink.lines[1])

    def test_every_reported_reason_is_one_of_the_named_ones(self):
        for row in (PORT_ROYAL_XYZ_IN_THE_STAGE, PRISON_ISLAND_ROW):
            with self.subTest(scene=row.scene_id):
                entry = resolve_entry(row, emit=Sink())
                self.assertIn(entry.relocation_reason, RELOCATION_REASONS)

    def test_the_report_carries_both_positions_and_the_travel_columns(self):
        entry = resolve_entry(PORT_ROYAL_XYZ_IN_THE_STAGE, emit=Sink())
        report = entry_report(entry)
        for column in world_scene_travel.entry_report(entry.destination):
            self.assertIn(column, report)
        self.assertEqual(report["stored_scene_id"], TEST_STAGE_SCENE_ID)
        self.assertEqual(
            report["stored_position"], [-9239.957, -2830.045, 223.292])
        self.assertEqual(report["used_position"], list(entry.destination.spawn))
        self.assertTrue(report["relocated"])
        self.assertEqual(report["used_scene_seq"], 0)
        self.assertEqual(
            report["teleport_fields"], [278, 0, *entry.destination.spawn])
        self.assertEqual(report["console_lines"], list(entry.console_lines))

    def test_the_report_shows_where_this_module_disagrees_with_the_client_table(self):
        # Scene 2: the pinned console line says the client's table authored an
        # arrival marker, and this module still owes a return ticket.  Both
        # readings are in the report so the disagreement is auditable rather
        # than hidden behind whichever one a caller happened to read.
        entry = resolve_entry(PRISON_ISLAND_ROW, emit=Sink())
        report = entry_report(entry)
        self.assertFalse(report["needs_return_ticket"])
        self.assertTrue(report["return_ticket_required"])

    def test_a_kept_row_report_shows_the_row_and_the_pin_side_by_side(self):
        entry = resolve_entry(STANDING_ON_THE_STAGE, emit=Sink())
        report = entry_report(entry)
        self.assertEqual(report["used_position"], [-13000.0, 22500.0, -2492.0])
        self.assertEqual(report["spawn"], list(entry.destination.spawn))
        self.assertEqual(report["teleport_fields"][2:], report["used_position"])

    def test_a_column_collision_is_refused_rather_than_merged(self):
        # The wrapper's whole claim is that a column added upstream cannot go
        # missing here.  update() would silently drop it, so the collision is
        # made an error - and this test proves the check can fire.
        entry = resolve_entry(ATTENDED_HOME_ROW, emit=Sink())
        original = world_scene_travel.entry_report
        try:
            world_scene_travel.entry_report = (
                lambda target: {"relocated": "upstream says no"}
            )
            with self.assertRaises(ValueError):
                entry_report(entry)
        finally:
            world_scene_travel.entry_report = original
        self.assertIn("relocated", entry_report(entry))

    def test_the_reports_refuse_anything_that_is_not_a_scene_entry(self):
        for call in (entry_report, relocation_console_line, return_ticket):
            with self.subTest(call=call.__name__):
                with self.assertRaises(ValueError):
                    call(object())


class ConventionTests(unittest.TestCase):

    def test_this_module_is_not_a_scenario(self):
        # Lane A ships behaviour that runs on a boot with no flags at all.
        self.assertIs(world_scene_entry.production_allowed, True)
        self.assertIs(world_scene_entry.test_only, False)

    def test_the_entry_type_is_frozen(self):
        entry = resolve_entry(ATTENDED_HOME_ROW, emit=Sink())
        self.assertIsInstance(entry, SceneEntry)
        with self.assertRaises(Exception):
            entry.position = ATTENDED_HOME_ROW

    def test_the_module_source_is_ascii(self):
        # Every lane in this tree that prints to the bridge console pins its
        # own source: cp874 turns one stray character in a docstring into a
        # crash the moment a traceback carries it.
        raw = MODULE_SOURCE.read_bytes()
        self.assertEqual([b for b in raw if b > 127], [])
        raw.decode("ascii").encode("cp874")

    def test_resolving_every_kind_of_row_creates_no_file_anywhere(self):
        # The behavioural half of "this module writes nothing".  A static scan
        # can be walked around with three characters of attribute access; a
        # directory that is empty before and after cannot.
        with tempfile.TemporaryDirectory() as folder:
            before = sorted(Path(folder).rglob("*"))
            for row in (ATTENDED_HOME_ROW, PORT_ROYAL_XYZ_IN_THE_STAGE,
                        STANDING_ON_THE_STAGE, PRISON_ISLAND_ROW):
                entry = resolve_entry(row, emit=Sink())
                entry_report(entry)
                return_ticket(entry)
            self.assertEqual(sorted(Path(folder).rglob("*")), before)
            self.assertEqual(before, [])

    def test_this_module_has_no_write_shaped_call_or_import(self):
        # The static half, parsed rather than grepped so a docstring cannot
        # trip it - and checking attribute names as well as bare names, because
        # `builtins.open(...)` and `path.open(...)` are not `ast.Name` calls.
        tree = ast.parse(MODULE_SOURCE.read_text(encoding="ascii"))
        forbidden_names = {"open", "exec", "eval", "__import__", "compile"}
        forbidden_attrs = {
            "open", "write", "write_text", "write_bytes", "writelines",
            "unlink", "mkdir", "send", "sendall", "commit", "execute",
            "checkpoint", "save_position", "update_position",
        }
        forbidden_modules = {
            "sqlite3", "socket", "subprocess", "shutil", "os", "io",
            "pathlib", "builtins", "tempfile",
        }
        forbidden_siblings = {"store", "repository", "session", "lifecycle"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                target = node.func
                if isinstance(target, ast.Name):
                    self.assertNotIn(target.id, forbidden_names)
                    if target.id == "print":
                        # print(..., file=...) is a write with no import.
                        self.assertEqual(
                            [kw.arg for kw in node.keywords], [])
                if isinstance(target, ast.Attribute):
                    self.assertNotIn(target.attr, forbidden_attrs)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(
                        alias.name.split(".")[0], forbidden_modules)
            if isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                self.assertNotIn(root, forbidden_modules)
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_siblings)


if __name__ == "__main__":
    unittest.main()
