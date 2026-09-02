"""The GT-192 preflight, and the one mistake it exists to not make.

``gm/warp_chain_preflight.py`` predicts, before an attended round is booked,
what the server will compose for every map ``/warp`` can reach.  The value of
such a tool is entirely in being right about the maps that are DIFFERENT, so
most of this file is about those:

* scene 2, whose roster ships from the runtime's own bg0002 arm.  The
  everyday arrival seam -- the one every other scene answers through --
  reports ``clear``/0 for it.  A preflight that trusted that seam would print
  ``0`` for the FIRST map on the owner's list and send a tester hunting a bug
  that is not there.  ``TheSceneTwoTrapTests`` measures both halves: that the
  seam really does say clear/0, and that the tool does not repeat it;
* scene 1, empty on arrival BY DESIGN and full one step later.  The tool must
  say ``empty_by_design``, not ``0``, or the tester grades the design as a
  FAIL;
* every other scene, whose count must come off the seam rather than off a
  label a lane handed over.

And one guard that is not about a scene at all: the runtime's bg0002 call
site is READ FROM SOURCE here, because this tool's scene-2 number is only
true while the tool calls that arm the way the runtime does.  If chief
changes those arguments, this file goes red rather than the tool quietly
lying to a tester.
"""

import ast
import contextlib
import dataclasses
import io
import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    lane_hooks,
    world_population,
    world_population_bg0002,
    world_population_handoff,
    world_scene_travel,
)
from pirateforce_foundation.gm import warp_chain_preflight as preflight  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_scene_census,
)
from pirateforce_foundation.gm.warp_executor import (  # noqa: E402
    warp_no_coords_live_target,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
RUNTIME_PATH = ROOT / "src" / "pirateforce_foundation" / "runtime.py"
MODULE_PATH = (
    ROOT / "src" / "pirateforce_foundation" / "gm" / "warp_chain_preflight.py"
)


# The lines ``render`` prints that are not scene rows, BY IDENTITY.  An
# earlier version of this round derived the number from ``len(render(()))``,
# which made three assertions compare ``render``'s output to ``render``'s own
# output: pf-adversary made ``render`` print PRECONDITION three times and the
# whole file stayed green, while the same mutant against the previous
# revision failed four tests (D3).  Naming them costs one edit when the output
# grows and buys back a check that can fail.
FRAMING_MARKERS = (" PRECONDITION ", " ROUTE ", " chain_scenes=", " NOTE ")


def _framing_lines() -> int:
    return len(FRAMING_MARKERS)


def _assert_framing_is_intact(case, lines):
    """Each framing line appears EXACTLY once, and nothing else is framing."""
    for marker in FRAMING_MARKERS:
        case.assertEqual(
            len([line for line in lines if marker in line]), 1,
            "framing line %r does not appear exactly once" % marker,
        )
    scene_lines = [line for line in lines if " scene=" in line]
    case.assertEqual(
        len(lines), len(scene_lines) + len(FRAMING_MARKERS),
        "render printed lines that are neither a scene row nor one of the "
        "four framing lines",
    )


def _enclosing_function(tree, node):
    """The ``FunctionDef`` a node sits in, or ``None``.

    Needed because ``ast.walk`` has no parents and a gate that searches the
    whole module is satisfied by dead code six thousand lines from the call it
    claims to pin -- measured, not imagined (pf-adversary D1, mutant 2).
    """
    for candidate in ast.walk(tree):
        if not isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if any(inner is node for inner in ast.walk(candidate)):
            return candidate
    return None


def _code_only(source: str) -> str:
    """``source`` with comments and string literals removed.

    A prose mention of a constant in a comment is not a use of it, and a test
    that cannot tell those apart forbids the module from EXPLAINING what it
    stopped doing -- which is the one thing a later reader needs most.
    """
    import tokenize
    kept = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        kept.append(token.string)
    return " ".join(kept)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class _Raises:
    """A legacy object every attribute access on explodes.

    Not ``None``: ``None`` might be handled by an ``is None`` branch
    somewhere and prove nothing about the failure path this tool promises.
    """

    def __getattr__(self, name):
        raise RuntimeError("legacy unavailable: " + name)


class TheChainIsTheOwnersOwnListTests(unittest.TestCase):
    """COO-DECISION 20260902_0544: scenes 2-11, 14, 130, closing with 1."""

    def test_the_reachable_set_is_the_thirteen_scenes_the_tester_types(self):
        self.assertEqual(
            preflight.reachable_scene_ids(),
            (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 130),
        )

    def test_the_gate_this_module_asks_is_the_production_gate(self):
        """Not a list in the module -- proved by MOVING the gate.

        The first version of this test re-typed the function's own
        comprehension and compared the result to itself; pf-adversary (D7)
        replaced the whole function body with a hardcoded thirteen-id tuple
        and it stayed green, along with every other test here.  A test that
        cannot tell "asks the gate" from "does not ask the gate" is not
        testing the sentence its name makes.

        So: shut one scene AT THE GATE and require the answer to follow.
        """
        real = preflight.warp_no_coords_live_target
        closed = []
        try:
            preflight.warp_no_coords_live_target = (
                lambda scene_id: None if scene_id == 130 else real(scene_id)
            )
            closed = list(preflight.reachable_scene_ids())
        finally:
            preflight.warp_no_coords_live_target = real
        self.assertNotIn(130, closed)
        self.assertIn(130, preflight.reachable_scene_ids())
        self.assertEqual(len(closed) + 1, len(preflight.reachable_scene_ids()))

    def test_scene_one_is_last_because_a_session_boots_there(self):
        rows = preflight.preflight_chain(legacy=_legacy())
        self.assertEqual([r.scene_id for r in rows][-1], world_population.SCENE_ID)
        self.assertEqual(
            [r.scene_id for r in rows],
            [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 130, 1],
        )


class TheSceneTwoTrapTests(unittest.TestCase):
    """The mistake this module was built around, pinned from both sides."""

    def test_the_everyday_seam_really_does_report_clear_zero_for_scene_two(self):
        """The premise.  If this ever stops being true the module's special
        case is dead weight and should be deleted, not left asserting."""
        scene_id = world_population_bg0002.SCENE2_N_ID
        anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(scene_id)
        )
        handoff = world_population_handoff.handoff_for_arrival(
            _legacy(), scene_id, anchor,
        )
        self.assertEqual(handoff.kind, world_population_handoff.KIND_CLEAR)
        self.assertEqual(int(handoff.actor_count), 0)
        self.assertIsNone(lane_hooks.scene_census_composer(scene_id))

    def test_the_preflight_does_not_repeat_the_seams_answer(self):
        row = preflight.preflight_for(
            world_population_bg0002.SCENE2_N_ID, legacy=_legacy()
        )
        self.assertEqual(row.source, preflight.SOURCE_RUNTIME_BG0002_ARM)
        self.assertTrue(row.on_arrival)
        self.assertIsNotNone(row.actor_count)
        self.assertGreater(row.actor_count, 0)

    def test_the_number_is_the_bg0002_arms_own_wire_count(self):
        scene_id = world_population_bg0002.SCENE2_N_ID
        anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(scene_id)
        )
        generation = world_population_bg0002.build_bg0002_population(
            _legacy(), anchor, scene_id=scene_id,
            count_source=world_population_bg0002.COUNT_SOURCE_FULL_ROSTER,
        )
        self.assertEqual(
            preflight.preflight_for(scene_id, legacy=_legacy()).actor_count,
            world_population_bg0002.wire_actor_count(generation),
        )

    def test_the_runtimes_own_call_site_still_passes_these_arguments(self):
        """READ FROM SOURCE, not imported.

        This tool's scene-2 number is only true while it calls the arm the
        way ``runtime.py`` does.  ``runtime.py`` is chief's file; this lane
        cannot stop it changing, but it can stop the change being silent.
        """
        source_text = RUNTIME_PATH.read_text(encoding="utf-8")
        # NAME COUNT FIRST, before any AST shape.  pf-adversary (D2b) added a
        # SECOND call site through a local alias -- `_b2 = ...
        # build_bg0002_population` then `_b2(legacy, anchor, 7, ...)` -- and
        # the first version of this guard, which counted only
        # `ast.Attribute` calls, stayed green while the wire shipped 7.
        self.assertEqual(
            source_text.count("build_bg0002_population"), 1,
            "runtime.py names build_bg0002_population more than once; an "
            "alias or a second call site can move scene 2's roster without "
            "this tool noticing",
        )
        tree = ast.parse(source_text)
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Attribute)
                 and node.func.attr == "build_bg0002_population")
                or (isinstance(node.func, ast.Name)
                    and node.func.id == "build_bg0002_population")
            )
        ]
        self.assertEqual(
            len(calls), 1,
            "runtime.py no longer has exactly one bg0002 build call; this "
            "tool's scene-2 prediction is derived from that one call site",
        )
        call = calls[0]
        # THE SUBSTANTIVE CHECK, and the one the first version of this test
        # did not make.  `actor_count` is the THIRD POSITIONAL parameter of
        # `build_bg0002_population`, so `legacy, anchor, 12, scene_id=...`
        # changes the roster from 97 to 12 while every keyword this test used
        # to read stays exactly as it was -- measured by pf-adversary (D2),
        # green on both test files, wire shipping 12.
        self.assertEqual(
            len(call.args), 2,
            "the runtime passes a third positional argument to the bg0002 "
            "arm; that position is actor_count, and this tool predicts the "
            "DEFAULT, so its scene-2 number is now wrong: "
            + ast.unparse(call),
        )
        keywords = {kw.arg for kw in call.keywords}
        self.assertNotIn(
            "actor_count", keywords,
            "the runtime now passes an explicit actor_count; this tool "
            "predicts the default and would now be wrong",
        )
        self.assertIn("scene_id", keywords)
        # `count_source` is a LABEL the arm records, not a count selector --
        # `build_bg0002_population` computes the count from `actor_count`
        # regardless of it.  Pinned because a change here still means someone
        # rethought this call, but named as the weaker check it is so a later
        # reader does not mistake it for the one that protects the 97.
        self.assertIn("count_source", keywords)


class TheOneMapThatIsEmptyOnPurposeTests(unittest.TestCase):
    """Scene 1.  ``empty_by_design`` and ``0`` are not the same sentence."""

    def test_scene_one_is_named_as_held_not_as_missing(self):
        row = preflight.preflight_for(world_population.SCENE_ID, legacy=_legacy())
        self.assertEqual(row.source, preflight.SOURCE_HELD_UNTIL_THE_PLAYER_MOVES)
        self.assertFalse(row.on_arrival)
        self.assertIn("ONE STEP", row.note.upper())

    def test_it_still_says_what_she_gets_after_the_step(self):
        """A tester who takes the step needs a number to compare against."""
        row = preflight.preflight_for(world_population.SCENE_ID, legacy=_legacy())
        self.assertIsNotNone(row.actor_count)
        self.assertGreater(row.actor_count, 0)

    def test_the_summary_separates_by_design_from_unexplained(self):
        lines = preflight.render(preflight.preflight_chain(legacy=_legacy()))
        summary = [line for line in lines if " chain_scenes=" in line]
        self.assertEqual(len(summary), 1, lines)
        self.assertIn("empty_until_you_step=[1]", summary[0])
        self.assertIn("shut_on_purpose=[]", summary[0])
        self.assertIn("empty_unexplained=[]", summary[0])


class TheCountsComeOffTheSeamTests(unittest.TestCase):
    def test_every_lane_composed_row_matches_an_independent_seam_read(self):
        # STILL WORTH ASSERTING, but it is no longer this file's proof of
        # correctness: pf-adversary (D1) measured that the seam and the
        # composer disagree exactly when a scene is shut, and the tool now
        # takes the composer's route.  Agreement here means every door is
        # open today, which is a fact worth pinning, not an independence
        # claim.
        rows = preflight.preflight_chain(legacy=_legacy())
        composed = [r for r in rows if r.source == preflight.SOURCE_LANE_COMPOSER]
        self.assertGreaterEqual(
            len(composed), 8,
            "a chain this short is not the world GM-A was rejected over",
        )
        for row in composed:
            with self.subTest(scene=row.scene_id):
                anchor = world_scene_travel.spawn_position(
                    world_scene_travel.destination(row.scene_id)
                )
                handoff = world_population_handoff.handoff_for_arrival(
                    _legacy(), row.scene_id, anchor,
                )
                self.assertEqual(
                    handoff.kind, world_population_handoff.KIND_CENSUS
                )
                self.assertEqual(row.actor_count, int(handoff.actor_count))
                self.assertTrue(row.on_arrival)


class ItFailsClosedAndNamedTests(unittest.TestCase):
    def test_a_scene_warp_refuses_is_not_reported_as_an_empty_map(self):
        """``/warp 278`` is REFUSED BY NAME.  Confusing that with an empty
        map is how a tester reports a bug against a command that never ran."""
        self.assertIsNone(warp_no_coords_live_target(278))
        row = preflight.preflight_for(278, legacy=_legacy())
        self.assertEqual(row.source, preflight.SOURCE_NOTHING)
        self.assertIsNone(row.actor_count)
        self.assertIn("refuses", row.note)

    def test_a_broken_legacy_leaves_every_row_named_and_countless(self):
        rows = preflight.preflight_chain(legacy=_Raises())
        self.assertEqual(len(rows), 13)
        for row in rows:
            with self.subTest(scene=row.scene_id):
                self.assertIsNone(
                    row.actor_count,
                    "a count survived a legacy that cannot answer -- it was "
                    "not read from the seam",
                )
                self.assertFalse(row.on_arrival)

    def test_a_composer_that_raises_is_not_reported_as_a_decline(self):
        """The runtime does not treat these as one event and neither may this.

        A DECLINE latches ``world_census_sent`` for that map alone; a RAISE
        latches ``world_census_refused``, which silences EVERY REMAINING MAP
        of the login until the next hop clears it.  An earlier version
        swallowed the exception type and printed the harmless word for both
        (pf-adversary D5).
        """
        row = preflight.preflight_for(3, legacy=_Raises())
        self.assertEqual(row.source, preflight.SOURCE_NOTHING)
        self.assertIsNone(row.actor_count)
        self.assertIn("raised", row.note)
        self.assertIn("RuntimeError", row.note)
        self.assertIn("world_census_refused", row.note)
        self.assertNotEqual(row.source, preflight.SOURCE_SHUT_TO_PLAYERS)

    def test_no_row_ever_reports_zero_in_place_of_unknown(self):
        for legacy in (_legacy(), _Raises()):
            for row in preflight.preflight_chain(legacy=legacy):
                with self.subTest(scene=row.scene_id):
                    self.assertNotEqual(
                        row.actor_count, 0,
                        "0 and 'do not know' must never be the same value",
                    )


class TheOutputAnOwnerCanPasteBackTests(unittest.TestCase):
    def test_every_line_is_ascii_and_carries_the_token(self):
        """The bridge console is cp874 (GT-145); scene 10 and 11's GM names
        are Thai, so this is not a hypothetical."""
        lines = preflight.render(preflight.preflight_chain(legacy=_legacy()))
        for line in lines:
            with self.subTest(line=line):
                line.encode("ascii")
                self.assertTrue(line.startswith(preflight.CONSOLE_TOKEN))

    def test_the_nonclaim_rides_the_output_not_only_the_docstring(self):
        """A tester reads the console, not this repository."""
        lines = preflight.render(preflight.preflight_chain(legacy=_legacy()))
        joined = " ".join(lines)
        self.assertIn("never what the client draws", joined)

    def test_the_summary_counts_the_chain_when_rows_arrive_as_a_generator(self):
        """The bug this assertion exists for was real and measured.

        ``len(tuple(rows))`` after the render loop counts an ALREADY WALKED
        generator, so the tool printed thirteen correct scene lines and then
        ``chain=0``.  The summary is the line a reader quotes.
        """
        rows = preflight.preflight_chain(legacy=_legacy())
        lines = preflight.render(row for row in rows)
        self.assertEqual(len(lines), len(rows) + _framing_lines())
        _assert_framing_is_intact(self, lines)
        summary = [line for line in lines if " chain_scenes=" in line]
        self.assertEqual(
            summary[0].split("chain_scenes=")[1].split()[0], str(len(rows))
        )
        self.assertEqual(lines, preflight.render(rows))

    def test_an_integer_scene_id_never_raises_however_odd(self):
        for scene_id in (-1, 10 ** 9, 0):
            with self.subTest(scene=scene_id):
                row = preflight.preflight_for(scene_id, legacy=_legacy())
                self.assertEqual(row.source, preflight.SOURCE_NOTHING)
                self.assertIsNone(row.actor_count)

    def test_a_bool_is_refused_by_type_and_never_answered_as_port_royal(self):
        """``True`` used to reach the registry and come back as Port Royal
        with "the registry does not pin a spawn" -- the one scene whose spawn
        is most certainly pinned, rendered as an unexplained empty map, while
        ``preflight_for(1)`` said 108 (pf-adversary D6).  Two entry points,
        opposite verdicts, one scene."""
        for scene_id in (True, False):
            with self.subTest(scene=scene_id):
                row = preflight.preflight_for(scene_id, legacy=_legacy())
                self.assertEqual(row.source, preflight.SOURCE_NOTHING)
                self.assertIsNone(row.actor_count)
                self.assertIn("must be an int", row.note)
                self.assertNotEqual(row.gm_name, "Port Royal")
        for scene_id in ("1", 1.0, b"1"):
            with self.subTest(scene=scene_id):
                self.assertIn(
                    "must be an int",
                    preflight.preflight_for(scene_id, legacy=_legacy()).note,
                )

    def test_a_precondition_line_plus_one_per_scene_plus_summary_plus_note(self):
        rows = preflight.preflight_chain(legacy=_legacy())
        lines = preflight.render(rows)
        self.assertEqual(len(lines), len(rows) + _framing_lines())
        _assert_framing_is_intact(self, lines)


class ItGrantsNobodyAnythingTests(unittest.TestCase):
    """Lane rule 1: nothing here may hand out GM, and nothing here sends."""

    def test_the_module_opens_no_socket_and_reads_no_account_list(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported.add(alias.name)
                imported.add(node.module or "")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
        for forbidden in ("socket", "accounts", "gm_accounts"):
            self.assertNotIn(forbidden, imported, forbidden)
        for forbidden in ("def send", "sendall", "production_allowed = True"):
            self.assertNotIn(forbidden, source, forbidden)



class TheThirdGateTests(unittest.TestCase):
    """pf-adversary D1: the gate the first version of this module skipped.

    The runtime asks THREE things before it ships a lane census -- a
    registered composer, ``module_production_allowed``, and the composer's
    own admission check ``lane_a_scene_census.scene_is_open_to_players``,
    which reads that scene's ``login_entry_allowed``.  The first version
    asked the first two and reached its number through
    ``handoff_for_arrival``, a route that never sees the third.  With scene
    10 shut it printed ``94 actors`` while the real dispatcher shipped
    nothing: a tester sent into a map closed ON PURPOSE, seeing the empty
    screen the design intends, and told by this tool's own NOTE line to file
    it as a real finding.

    That is not hypothetical.  Scenes 17 and 126 are ``login_entry_allowed:
    false`` in the shipped registry right now, and
    ``lane_a_scene_census.py``'s own docstring records scenes 4 and 10
    sitting shut for rounds.
    """

    @staticmethod
    def _registry_with_scene_shut(scene_id):
        registry = world_scene_travel.load_scene_registry()
        destinations = tuple(
            dataclasses.replace(value, login_entry_allowed=False)
            if getattr(value, "n_id", None) == scene_id else value
            for value in registry.destinations
        )
        return dataclasses.replace(registry, destinations=destinations)

    def test_a_scene_shut_to_players_is_its_own_answer_not_a_count(self):
        shut = self._registry_with_scene_shut(10)
        self.assertFalse(lane_a_scene_census.scene_is_open_to_players(10, shut))
        row = preflight.preflight_for(
            10, legacy=_legacy(), scene_entry_registry=shut,
        )
        self.assertEqual(row.source, preflight.SOURCE_SHUT_TO_PLAYERS)
        self.assertIsNone(row.actor_count)
        self.assertFalse(row.on_arrival)
        self.assertIn("SHUT ON PURPOSE", row.note)

    def test_the_seam_would_still_have_answered_with_a_roster(self):
        """The premise of D1, measured: the two routes really do disagree,
        and only for a shut scene.  If this ever stops being true the special
        handling is dead weight and should be deleted, not left asserting."""
        shut = self._registry_with_scene_shut(10)
        anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(10)
        )
        handoff = world_population_handoff.handoff_for_arrival(
            _legacy(), 10, anchor,
        )
        self.assertEqual(handoff.kind, world_population_handoff.KIND_CENSUS)
        self.assertGreater(int(handoff.actor_count), 0)
        self.assertIsNone(
            preflight.preflight_for(
                10, legacy=_legacy(), scene_entry_registry=shut,
            ).actor_count,
            "the tool followed the seam instead of the composer",
        )

    def test_a_shut_scene_is_not_swept_into_empty_unexplained(self):
        shut = self._registry_with_scene_shut(10)
        lines = preflight.render(
            preflight.preflight_chain(legacy=_legacy(), scene_entry_registry=shut)
        )
        summary = [line for line in lines if " chain_scenes=" in line][0]
        self.assertIn("shut_on_purpose=[10]", summary)
        self.assertIn("empty_unexplained=[]", summary)
        scene_line = [line for line in lines if " scene=10 " in line][0]
        self.assertIn("SHUT_ON_PURPOSE", scene_line)

    def test_the_count_is_read_off_the_composed_bytes_not_off_the_label(self):
        """A label is an integer a lane handed over; the runtime's own
        comment at that hand-off calls it untrusted."""
        composer = lane_hooks.scene_census_composer(3)
        anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(3)
        )
        result = composer.compose(
            legacy=_legacy(), anchor=anchor, scene_id=3,
            scene_entry_registry=world_scene_travel.load_scene_registry(),
        )
        self.assertEqual(
            preflight.preflight_for(3, legacy=_legacy()).actor_count,
            world_population_handoff.wire_count_of(result.pc),
        )


class ThePreconditionThatCanInvalidateEveryRowTests(unittest.TestCase):
    """pf-adversary D3.  A boot that fails it ships no census on ANY map."""

    def test_the_precondition_leads_the_output(self):
        lines = preflight.render(preflight.preflight_chain(legacy=_legacy()))
        self.assertTrue(lines[0].startswith(preflight.CONSOLE_TOKEN))
        self.assertIn("PRECONDITION", lines[0])
        self.assertIn("second_password_mode=required", lines[0])
        self.assertIn("that is the boot, not a bug", lines[0])

    def test_the_condition_it_names_is_the_one_runtime_actually_applies(self):
        """READ FROM SOURCE.  If chief changes the arming condition, this
        goes red rather than the tool reassuring a tester about a boot rule
        that no longer exists."""
        source = RUNTIME_PATH.read_text(encoding="utf-8")
        self.assertIn("world_census_enabled = (", source)
        armed = source.split("world_census_enabled = (", 1)[1].split(")", 1)[0]
        self.assertIn("not active_lanes", armed)
        self.assertIn('second_password_mode == "required"', armed)
        self.assertIn("and", armed)


class TheEntryPointAHumanActuallyRunsTests(unittest.TestCase):
    """pf-adversary D8: ``main()`` was the only thing anyone runs, untested."""

    @staticmethod
    def _run(argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = preflight.main(argv)
        return code, out.getvalue().splitlines()

    def test_no_arguments_runs_the_whole_reachable_world(self):
        code, lines = self._run([])
        self.assertEqual(code, 0)
        self.assertEqual(
            len(lines),
            len(preflight.reachable_scene_ids()) + _framing_lines(),
        )
        _assert_framing_is_intact(self, lines)
        for line in lines:
            line.encode("cp874")
            self.assertTrue(line.startswith(preflight.CONSOLE_TOKEN))

    def test_positional_scene_ids_run_a_custom_chain(self):
        code, lines = self._run(["3", "14"])
        self.assertEqual(code, 0)
        self.assertEqual(len(lines), 2 + _framing_lines())
        scene_lines = [line for line in lines if " scene=" in line]
        self.assertEqual(len(scene_lines), 2, lines)
        self.assertIn(" scene=3 ", scene_lines[0])
        self.assertIn(" scene=14 ", scene_lines[1])

    def test_a_junk_argument_is_refused_by_name_and_not_a_traceback(self):
        """It used to die with a bare ``ValueError`` from ``int()`` and print
        zero lines -- a fail-closed promise that stopped at the front door."""
        code, lines = self._run(["abc"])
        self.assertNotEqual(code, 0)
        self.assertTrue(lines)
        self.assertIn("abc", lines[0])
        self.assertTrue(lines[0].startswith(preflight.CONSOLE_TOKEN))

    def test_an_exit_code_a_wrapper_can_gate_on(self):
        """``main()`` returned 0 whether every scene resolved or none did, so
        nothing could gate on it (D8)."""
        self.assertEqual(self._run(["3"])[0], 0)
        self.assertNotEqual(
            self._run(["278"])[0], 0,
            "a chain whose every scene is unexplained still exits 0",
        )


class TheBranchesThatHadNeverRunTests(unittest.TestCase):
    """pf-adversary D8: two fail-closed arms with no test at all, in a file
    that argues at ``_composed_count`` that a branch no test kills is not a
    branch."""

    def test_a_composer_whose_module_is_not_production_allowed(self):
        composer = lane_hooks.scene_census_composer(3)
        replaced = composer._replace(module="pirateforce_foundation.nope")
        real = lane_hooks.scene_census_composer
        try:
            lane_hooks.scene_census_composer = (
                lambda scene_id: replaced if scene_id == 3 else real(scene_id)
            )
            preflight.lane_hooks.scene_census_composer = (
                lane_hooks.scene_census_composer
            )
            row = preflight.preflight_for(3, legacy=_legacy())
        finally:
            lane_hooks.scene_census_composer = real
            preflight.lane_hooks.scene_census_composer = real
        self.assertEqual(row.source, preflight.SOURCE_NOTHING)
        self.assertIsNone(row.actor_count)
        self.assertIn("not production-allowed", row.note)

    def test_a_reachable_scene_no_arm_claims(self):
        real = lane_hooks.scene_census_composer
        try:
            lane_hooks.scene_census_composer = (
                lambda scene_id: None if scene_id == 3 else real(scene_id)
            )
            preflight.lane_hooks.scene_census_composer = (
                lane_hooks.scene_census_composer
            )
            row = preflight.preflight_for(3, legacy=_legacy())
        finally:
            lane_hooks.scene_census_composer = real
            preflight.lane_hooks.scene_census_composer = real
        self.assertEqual(row.source, preflight.SOURCE_NOTHING)
        self.assertIsNone(row.actor_count)
        self.assertIn("no lane composer claims it", row.note)


class TheNumberThatWasComputedAndShownToNobodyTests(unittest.TestCase):
    """Scene 1's after-one-step count, on the console instead of in a field.

    The chain the owner types CLOSES on scene 1, and ``COO-DECISION
    2026-09-02T05:44+07:00`` says to judge that map only after one step.  The
    count for that step has been in ``ScenePreflight.actor_count`` since the
    module shipped, and ``test_it_still_says_what_she_gets_after_the_step``
    above has asserted it is there -- but ``render`` printed ``0`` for that row
    and dropped it, so the console she actually reads carried no number for the
    last map of her own chain.  A test whose name promises an answer, pinning a
    field nobody prints, is the same defect pf-adversary logged as D4.
    """

    def test_the_step_count_reaches_the_console(self):
        lines = preflight.render(preflight.preflight_chain(legacy=_legacy()))
        home = [
            line for line in lines
            if " scene=%d " % world_population.SCENE_ID in line
        ]
        self.assertEqual(len(home), 1, lines)
        row = preflight.preflight_for(
            world_population.SCENE_ID, legacy=_legacy()
        )
        self.assertIn(
            "actors_after_one_step=%d" % row.actor_count, home[0],
            "the one map that is empty when she lands prints no number for "
            "what she gets after the step: " + home[0],
        )
        # And the arrival half must still read 0, or the fix would have
        # erased the distinction the module exists to make.
        self.assertIn("actors_on_arrival=0 ", home[0])

    def test_every_other_row_says_n_a_and_never_zero(self):
        """``n/a`` is a refusal to predict.  ``0`` would read as a bug."""
        lines = [
            line
            for line in preflight.render(
                preflight.preflight_chain(legacy=_legacy())
            )
            if " scene=" in line
        ]
        home_marker = " scene=%d " % world_population.SCENE_ID
        others = [line for line in lines if home_marker not in line]
        self.assertTrue(others)
        for line in others:
            self.assertIn("actors_after_one_step=n/a", line, line)
            self.assertNotIn("actors_after_one_step=0", line, line)

    def test_the_field_is_keyed_on_the_source_not_on_arrival(self):
        """A shut map is also ``on_arrival=False`` and must NOT get a step
        number: nothing arrives there at all, before or after a step."""
        shut = preflight.ScenePreflight(
            scene_id=10, gm_name="x", source=preflight.SOURCE_SHUT_TO_PLAYERS,
            route=preflight.ROUTE_PRODUCTION_COMPOSER, module="m",
            actor_count=94, on_arrival=False, note="shut",
        )
        line = [
            line for line in preflight.render((shut,)) if " scene=10 " in line
        ][0]
        self.assertIn("actors_after_one_step=n/a", line)
        self.assertNotIn("94", line)


class TheOutputSaysWhichNumbersItDerivedAndWhichItCopiedTests(unittest.TestCase):
    """pf-adversary's closing question from round ``0aij4z``, answered.

    He asked: when this tool and the runtime disagree, what in the OUTPUT
    tells her which to doubt?  For the eleven composer scenes the answer was
    already "nothing to doubt" -- the tool walks the runtime's own route.  For
    scenes 1 and 2 it RECONSTRUCTS a call inside ``runtime.py``, a file this
    lane may not touch, and the output said nothing about the difference.  Now
    every row carries its route and the summary lists the reconstructed ones.
    """

    def test_every_row_carries_a_route_from_the_named_set(self):
        rows = preflight.preflight_chain(legacy=_legacy())
        allowed = {
            preflight.ROUTE_PRODUCTION_COMPOSER,
            preflight.ROUTE_MIRRORED_RUNTIME_ARM,
            preflight.ROUTE_NONE,
        }
        for row in rows:
            self.assertIn(row.route, allowed, row)

    def test_the_two_arms_are_the_mirrored_ones_and_the_rest_are_not(self):
        rows = {
            row.scene_id: row
            for row in preflight.preflight_chain(legacy=_legacy())
        }
        self.assertEqual(
            rows[world_population.SCENE_ID].route,
            preflight.ROUTE_MIRRORED_RUNTIME_ARM,
        )
        self.assertEqual(
            rows[world_population_bg0002.SCENE2_N_ID].route,
            preflight.ROUTE_MIRRORED_RUNTIME_ARM,
        )
        composed = [
            row for row in rows.values()
            if row.source == preflight.SOURCE_LANE_COMPOSER
        ]
        self.assertTrue(composed)
        for row in composed:
            self.assertEqual(row.route, preflight.ROUTE_PRODUCTION_COMPOSER)

    def test_a_scene_refused_by_name_claims_no_route_at_all(self):
        row = preflight.preflight_for(999999, legacy=_legacy())
        self.assertEqual(row.route, preflight.ROUTE_NONE)

    def test_the_console_prints_the_route_on_every_row_and_the_legend_once(self):
        lines = preflight.render(preflight.preflight_chain(legacy=_legacy()))
        legend = [line for line in lines if " ROUTE " in line]
        self.assertEqual(len(legend), 1, lines)
        self.assertIn("mirrored_runtime_arm", legend[0])
        self.assertIn("--world-census-actors", legend[0])
        for line in [line for line in lines if " scene=" in line]:
            self.assertIn("route=", line, line)

    def test_the_summary_lists_the_reconstructed_scenes(self):
        lines = preflight.render(preflight.preflight_chain(legacy=_legacy()))
        summary = [line for line in lines if " chain_scenes=" in line][0]
        self.assertIn(
            "mirrored_not_measured=[%d,%d]"
            % (
                world_population_bg0002.SCENE2_N_ID,
                world_population.SCENE_ID,
            ),
            summary,
        )


class TheHomeArmIsMirroredFromTheRuntimesOwnExpressionTests(unittest.TestCase):
    """Scene 1's count, pinned to the call ``runtime.py`` actually makes.

    MEASURED FIRST, so nobody reads more into this than it says: on this
    clone the old spelling (``effective_actor_count()`` with
    ``COUNT_SOURCE_MEASURED_CEILING`` hand-picked beside it) and the runtime's
    own ``census_count_for_dispatch()`` build BYTE-IDENTICAL frames, both
    reporting 108 on the wire.  The printed number was never wrong.  What
    differed was the RECORDED REASON -- ``measured_client_ceiling`` where the
    runtime records ``full_census`` -- which is exactly the misreport
    ``census_count_for_dispatch``'s own docstring says it exists to prevent,
    and it is the kind of difference that stays invisible until the day a
    ceiling is finally measured and the two spellings stop agreeing.
    """

    def test_the_module_takes_the_count_from_the_runtimes_own_call(self):
        """A SOURCE PIN, and weaker than a behavioural test on purpose.

        It cannot be a behavioural test today: measured above, both spellings
        build byte-identical frames, so no assertion on the OUTPUT can tell
        them apart.  The difference is the recorded reason, and it only
        becomes a difference in bytes on the day a client ceiling is finally
        measured.  So this pins the spelling and says plainly that is all it
        does.
        """
        code = _code_only(MODULE_PATH.read_text(encoding="utf-8"))
        self.assertIn("census_count_for_dispatch", code)
        self.assertNotIn(
            "COUNT_SOURCE_MEASURED_CEILING", code,
            "the home branch hand-picks a count_source again; the runtime "
            "takes the number and its reason from one call",
        )

    def test_the_home_count_still_matches_the_runtimes_expression(self):
        count, count_source = world_population.census_count_for_dispatch()
        anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(world_population.SCENE_ID)
        )
        generation = world_population.build_world_population(
            _legacy(), anchor, count,
            scene_id=world_population.SCENE_ID, count_source=count_source,
        )
        self.assertEqual(
            preflight.preflight_for(
                world_population.SCENE_ID, legacy=_legacy()
            ).actor_count,
            world_population.wire_actor_count(generation),
        )

    def test_the_runtimes_home_call_site_still_looks_like_this(self):
        """READ FROM SOURCE, the same guard scene 2 already has.

        Scene 2 got this gate because pf-adversary moved its roster with a
        positional argument and an alias while both test files stayed green.
        Scene 1's arm had no such gate at all, and it is the arm with the
        EXTRA moving part: a boot flag (``--world-census-actors``) selects
        another rung for this scene alone.
        """
        source_text = RUNTIME_PATH.read_text(encoding="utf-8")
        # Count CODE occurrences only.  The name appears once more in a
        # docstring on line 338, and an alias assignment -- the trick that
        # defeated scene 2's first gate -- is code, so tokenising is what
        # separates the two.  A plain `str.count` would either miss the alias
        # or trip on the prose.
        import tokenize
        code_uses = 0
        readline = io.StringIO(source_text).readline
        for token in tokenize.generate_tokens(readline):
            if (token.type == tokenize.NAME
                    and token.string == "build_world_population"):
                code_uses += 1
        self.assertEqual(
            code_uses, 1,
            "runtime.py uses build_world_population in code more than once; "
            "an alias or a second call site can move scene 1's roster "
            "without this tool noticing",
        )
        tree = ast.parse(source_text)
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Attribute)
                 and node.func.attr == "build_world_population")
                or (isinstance(node.func, ast.Name)
                    and node.func.id == "build_world_population")
            )
        ]
        self.assertEqual(len(calls), 1, "expected exactly one home build call")
        call = calls[0]
        self.assertEqual(
            len(call.args), 3,
            "the home arm's third positional argument is the count this tool "
            "predicts; the call site's shape changed: " + ast.unparse(call),
        )
        self.assertIsInstance(
            call.args[2], ast.Name,
            "the count is no longer a name bound above the call, so the "
            "expression this tool mirrors cannot be read: "
            + ast.unparse(call),
        )
        bound = call.args[2].id
        # SCOPED TO THE ENCLOSING FUNCTION, AND TO THE FLAGLESS ARM.  The
        # first version of this gate walked the WHOLE of runtime.py and asked
        # only that the two substrings appear SOMEWHERE among the assignments
        # binding that name -- possibly in different assignments, in different
        # functions, on either arm of the conditional.  pf-adversary broke it
        # twice in ten minutes and both mutants left this file green:
        #   * INVERTED the two arms, so a flagless boot took
        #     `effective_actor_count(20)` and shipped 20 while this tool kept
        #     printing 108 -- a tester counts twenty NPCs after her step and
        #     files a FAIL for GT-192 that is a mirror drift, not a bug;
        #   * put a literal `count = 20` at the live call site and left a
        #     DEAD, never-called function at the end of the file holding the
        #     old tuple-assign for this gate to find.
        # What the mirror actually depends on is one property -- WHICH ARM A
        # FLAGLESS BOOT TAKES -- so that is what is asserted now.
        enclosing = _enclosing_function(tree, call)
        self.assertIsNotNone(
            enclosing, "the home build call is not inside a function any more"
        )
        assigns = [
            node for node in ast.walk(enclosing)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Tuple)
                and any(
                    isinstance(element, ast.Name) and element.id == bound
                    for element in target.elts
                )
                for target in node.targets
            )
        ]
        self.assertTrue(
            assigns,
            "nothing in the function that builds the home census binds %r "
            "alongside its reason any more; this lane's tool mirrors that "
            "expression, so the mirror needs updating -- this is a GM-lane "
            "diagnostic's dependency on your call site, not a rule about it"
            % bound,
        )
        conditionals = [
            node.value for node in assigns
            if isinstance(node.value, ast.IfExp)
        ]
        self.assertTrue(
            conditionals,
            "the home count is no longer chosen by an inline conditional, so "
            "this gate cannot read which arm a flagless boot takes; the "
            "scene-1 mirror needs re-deriving by hand: "
            + " | ".join(ast.unparse(node.value) for node in assigns),
        )
        flagless = [
            node for node in conditionals
            if ast.unparse(node.test) == "world_census_actor_count is None"
        ]
        self.assertTrue(
            flagless,
            "the flagless boot is no longer selected by "
            "`world_census_actor_count is None`; the ROUTE legend tells the "
            "tester about a flag whose rung this gate can no longer find: "
            + " | ".join(ast.unparse(node) for node in conditionals),
        )
        for node in flagless:
            self.assertIn(
                "census_count_for_dispatch()", ast.unparse(node.body),
                "the arm a FLAGLESS boot takes no longer calls "
                "census_count_for_dispatch(); this tool's scene-1 number "
                "mirrors that call and is now predicting the wrong rung: "
                + ast.unparse(node),
            )

class _FakeComposed:
    """A composer result whose LABEL and whose BYTES disagree on purpose."""

    def __init__(self, wire_count, label):
        header = bytearray(world_population_handoff.WIRE_HEADER_BYTES)
        offset = world_population_handoff.WIRE_COUNT_TAG_OFFSET
        header[offset] = world_population_handoff.COLLECTION_TAG
        header[offset + 1:offset + 3] = int(wire_count).to_bytes(2, "little")
        self.pc = bytes(header)
        self.actor_count = label


class _RecordingComposer:
    def __init__(self, module, result):
        self.module = module
        self.result = result
        self.calls = []

    def compose(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class WhatProductionComposerActuallyPromisesTests(unittest.TestCase):
    """The label says HOW the number was obtained.  Pin both halves of it.

    pf-adversary (D6) mutated ``_composed_count`` twice -- reading
    ``result.actor_count`` (the lane-authored label this module's own
    docstring calls untrusted) instead of the queued bytes, and composing at
    ``(0,0,0)`` instead of the scene's pinned spawn -- and BOTH left the whole
    file green with byte-identical console output, because the label happens to
    equal the wire count today and the count happens not to move with the
    anchor.  A route label is a promise about the implementation, so the
    implementation needs a test that holds it: the rows advertised as MEASURED
    had no gate at all while the two reconstructed rows had two.
    """

    @staticmethod
    def _with_composer(scene_id, composer, allowed=True):
        real_composer = lane_hooks.scene_census_composer
        real_allowed = lane_hooks.module_production_allowed
        try:
            lane_hooks.scene_census_composer = (
                lambda sid: composer if sid == scene_id else real_composer(sid)
            )
            lane_hooks.module_production_allowed = (
                lambda module: True if module == composer.module
                else real_allowed(module)
            )
            preflight.lane_hooks.scene_census_composer = (
                lane_hooks.scene_census_composer
            )
            preflight.lane_hooks.module_production_allowed = (
                lane_hooks.module_production_allowed
            )
            return preflight.preflight_for(scene_id, legacy=_legacy())
        finally:
            lane_hooks.scene_census_composer = real_composer
            lane_hooks.module_production_allowed = real_allowed
            preflight.lane_hooks.scene_census_composer = real_composer
            preflight.lane_hooks.module_production_allowed = real_allowed

    def test_the_number_is_the_queued_bytes_not_the_lanes_own_label(self):
        composer = _RecordingComposer(
            "fake_lane_module", _FakeComposed(wire_count=7, label=56)
        )
        row = self._with_composer(3, composer)
        self.assertEqual(row.route, preflight.ROUTE_PRODUCTION_COMPOSER)
        self.assertEqual(
            row.actor_count, 7,
            "the row reports the label a lane handed over, not the count in "
            "the bytes that would be queued; a label can say 56 over an "
            "empty buffer",
        )

    def test_the_composer_is_called_at_the_scenes_pinned_spawn(self):
        composer = _RecordingComposer(
            "fake_lane_module", _FakeComposed(wire_count=7, label=7)
        )
        self._with_composer(3, composer)
        self.assertEqual(len(composer.calls), 1)
        self.assertEqual(
            composer.calls[0]["anchor"],
            world_scene_travel.spawn_position(
                world_scene_travel.destination(3)
            ),
            "every row prints why=...at this scene's pinned spawn; the "
            "composer was called somewhere else",
        )
        self.assertEqual(composer.calls[0]["scene_id"], 3)


class TheConsoleNeverInventsAZeroTests(unittest.TestCase):
    """pf-adversary D8: ``0`` reached rows where nothing is known."""

    def test_a_scene_refused_by_name_prints_n_a_not_zero(self):
        lines = preflight.render(
            preflight.preflight_chain([12], legacy=_legacy())
        )
        row = [line for line in lines if " scene=12 " in line][0]
        self.assertIn("actors_on_arrival=n/a", row)
        self.assertNotIn("actors_on_arrival=0", row)

    def test_the_two_rows_where_zero_is_the_prediction_keep_it(self):
        held = preflight.preflight_for(
            world_population.SCENE_ID, legacy=_legacy()
        )
        shut = preflight.ScenePreflight(
            scene_id=10, gm_name="x", source=preflight.SOURCE_SHUT_TO_PLAYERS,
            route=preflight.ROUTE_PRODUCTION_COMPOSER, module="m",
            actor_count=None, on_arrival=False, note="shut",
        )
        lines = preflight.render((held, shut))
        for marker in (" scene=%d " % world_population.SCENE_ID, " scene=10 "):
            line = [line for line in lines if marker in line][0]
            self.assertIn("actors_on_arrival=0", line, line)

    def test_the_legend_names_every_route_the_console_can_print(self):
        """``route=none`` reached her console while the legend defined two
        values; a mistyped scene number is how she meets it (D5)."""
        legend = [
            line for line in preflight.render(())
            if " ROUTE " in line
        ][0]
        for route in (
            preflight.ROUTE_PRODUCTION_COMPOSER,
            preflight.ROUTE_MIRRORED_RUNTIME_ARM,
            preflight.ROUTE_NONE,
        ):
            self.assertIn(route + "=", legend, route)

    def test_the_legend_names_the_anchor_caveat_the_gate_cannot_close(self):
        """The runtime composes scene 1 at the position she STEPPED TO
        (``runtime.py`` home arm, from ``last_target_pos``); this tool
        composes at the pinned spawn.  Measured: the count does not move with
        the anchor today.  Named because no gate closes it (D7)."""
        legend = [
            line for line in preflight.render(()) if " ROUTE " in line
        ][0]
        self.assertIn("STEPPED TO", legend)
        self.assertIn("pinned spawn", legend)


if __name__ == "__main__":
    unittest.main()


class WhatChiefsLetter1712AskedForTests(unittest.TestCase):
    """The two asks of `20260902_1712_CHIEF-TO-LANE-GM-gt192-debt-paid-*`.

    Both are about ONE thing: what the tester's eye actually meets on the
    console during `GT-192`.  Neither changes a number this tool derives.
    """

    def test_the_note_says_a_skipped_scene_is_not_an_empty_one(self):
        rows = preflight.preflight_chain(legacy=_legacy())
        note = [line for line in preflight.render(rows) if " NOTE " in line]
        self.assertEqual(len(note), 1, "the note is one framing line")
        self.assertIn("LANE_A_CENSUS_SKIPPED", note[0])
        self.assertIn("NOT a licence for an empty map", note[0])

    def test_the_notes_count_is_the_rows_count_not_a_typed_in_number(self):
        rows = preflight.preflight_chain(legacy=_legacy())
        mirrored = [
            row for row in rows
            if row.source == preflight.SOURCE_RUNTIME_BG0002_ARM
        ]
        self.assertTrue(mirrored, "the reachable world still has scene 2")
        note = [line for line in preflight.render(rows) if " NOTE " in line][0]
        for row in mirrored:
            with self.subTest(scene=row.scene_id):
                self.assertIn("map %d " % row.scene_id, note)
                self.assertIn("%d actors" % row.actor_count, note)

    def test_a_chain_without_the_mirrored_arm_gets_no_clause(self):
        # The clause is derived, so a chain that never touches scene 2 must
        # not carry a sentence about scene 2.
        rows = preflight.preflight_chain([3, 14], legacy=_legacy())
        note = [line for line in preflight.render(rows) if " NOTE " in line][0]
        self.assertNotIn("LANE_A_CENSUS_SKIPPED", note)

    def test_the_precondition_is_the_first_line_on_a_real_console(self):
        """Ask (a), measured the only way that can prove it: a real run.

        Importing this module registers the lane hooks, which write 28 lines
        to STDERR before `main()` gets to print anything.  In a console where
        both streams land together -- the tester's -- that pushed the
        PRECONDITION to roughly line 29.  Asserting on `render()` cannot see
        this at all; only a subprocess can.
        """
        import subprocess

        proc = subprocess.run(
            [sys.executable, "-m",
             "pirateforce_foundation.gm.warp_chain_preflight", "3"],
            cwd=str(ROOT),
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        first = proc.stderr.splitlines()[0]
        self.assertTrue(
            first.startswith(
                "%s PRECONDITION " % preflight.CONSOLE_TOKEN
            ),
            "the first stderr line is %r, so the boot precondition is not "
            "what she reads first" % first,
        )
        # And stdout keeps its own line 1, so a redirected capture is
        # unchanged for anyone reading the file afterwards.
        self.assertTrue(
            proc.stdout.splitlines()[0].startswith(
                "%s PRECONDITION " % preflight.CONSOLE_TOKEN
            )
        )

    def test_an_importer_never_gets_the_stderr_line(self):
        """The guard is `__main__`-only: a test run must stay quiet."""
        import subprocess

        proc = subprocess.run(
            [sys.executable, "-c",
             "import pirateforce_foundation.gm.warp_chain_preflight"],
            cwd=str(ROOT),
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        self.assertNotIn("GM_WARP_PREFLIGHT PRECONDITION", proc.stderr)
        self.assertEqual(proc.stdout, "")
