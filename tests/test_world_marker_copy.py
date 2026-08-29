"""The gate-side half of COO-DECISION 20260829_0941: no skip, no bridge.

WHAT MAKES THIS FILE DIFFERENT FROM ``test_world_scene_marker.py``.  That file
has one test that ties ``world_scene_marker._ROWS`` to the client's tables and
it is ``@BRIDGE_GAMEDATA.skip_unless_present()`` -- so on the Windows gate,
the machine that decides whether a change merges, it does not run.
pf-adversary measured the consequence in round ``8ubiku2`` (E1): forge a
coordinate, update the by-value pin to match, move the registry spawn to
match, and the suite is green with a fabricated point wearing the label
``client_marker_table``.

Every test in this file runs on every machine.  There is no skip decorator
here and ``test_this_file_never_learns_to_skip`` fails if a later round adds
one -- the COO's ruling says the re-derive test may not skip, and a rule that
lives only in a letter is a rule the gate cannot enforce.

WHAT THESE TESTS DO AND DO NOT ESTABLISH.  They establish that the literals in
``world_scene_marker`` are a faithful projection of
``world_data/world_marker_crosswalk.json``, and that the JSON's bytes are the
bytes ``world_marker_copy.COPY_SHA256`` pins.  They do NOT establish that the
JSON matches the client: the client's tables are not in this repository.  That
hop is ``verify_against_sources()``, run from
``MarkerReverificationOnTheBridgeTest``, and it is still bridge-only.  The
difference the ruling bought is in what a wrong number now costs: an accident
cannot survive at all, and a forgery needs four coordinated edits that all
appear in one diff.
"""

import ast
import copy as copy_module
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_marker_copy  # noqa: E402
from pirateforce_foundation import world_scene_marker  # noqa: E402
from pirateforce_foundation.world_marker_copy import (  # noqa: E402
    MarkerCopyError,
    derive_census,
    derive_rows,
    load_copy,
    s32,
)


class TheCopyIsTheOneThatIsPinnedTest(unittest.TestCase):
    """Part 2 of the ruling: the digest, and both directions it can break."""

    def test_the_committed_bytes_are_the_pinned_bytes(self):
        raw = world_marker_copy.COPY_PATH.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(), world_marker_copy.COPY_SHA256
        )

    def test_editing_the_copy_without_moving_the_pin_is_refused(self):
        """The mutation the pin exists for, executed rather than described."""
        document = json.loads(
            world_marker_copy.COPY_PATH.read_text(encoding="utf-8")
        )
        document["marker_rows_verbatim"]["1"]["raw"]["n_X"] = "4294956975"
        with tempfile.TemporaryDirectory() as work:
            forged = Path(work) / "world_marker_crosswalk.json"
            forged.write_text(json.dumps(document, indent=1) + "\n",
                              encoding="utf-8")
            original = world_marker_copy.COPY_PATH
            world_marker_copy.COPY_PATH = forged
            try:
                with self.assertRaises(MarkerCopyError) as caught:
                    load_copy()
            finally:
                world_marker_copy.COPY_PATH = original
        self.assertIn("sha256 mismatch", str(caught.exception))

    def test_a_missing_copy_is_an_error_and_not_an_empty_answer(self):
        original = world_marker_copy.COPY_PATH
        world_marker_copy.COPY_PATH = original.parent / "no_such_file.json"
        try:
            with self.assertRaises(MarkerCopyError):
                load_copy()
        finally:
            world_marker_copy.COPY_PATH = original


class ThePinnedRowsAreAProjectionOfTheCopyTest(unittest.TestCase):
    """Part 1 of the ruling: ``_ROWS`` bound to a committed artifact."""

    def setUp(self):
        self.document = load_copy()

    def test_every_pinned_row_re_derives_from_the_copy(self):
        self.assertEqual(derive_rows(self.document), world_scene_marker._ROWS)

    def test_every_scene_that_names_a_marker_is_covered_by_the_copy(self):
        """A copy missing one of the 13 rows must not read as agreement.

        ~~``assertTrue(all(len(row) == 7 ...))``~~ was here and could not fail
        for any input: ``derive_rows`` appends a 7-element tuple literal, so
        the assertion restated the code it was checking - the round-``uajlve``
        defect this file's own docstring warns about (pf-adversary, round
        i8timv, D7). What replaces it is the property that can actually break:
        the copy's scene index must name a marker for exactly the scenes
        ``_ROWS`` covers, so dropping a row from either side is a mismatch
        rather than a shorter agreement.
        """
        named = tuple(
            scene for scene, marker in self.document["scene_marker_index"]
            if marker
        )
        self.assertEqual(named, tuple(row[0] for row in world_scene_marker._ROWS))
        self.assertEqual(len(named), world_scene_marker.SCENES_WITH_A_MARKER)

    def test_forging_a_coordinate_in_the_copy_turns_this_file_red(self):
        """The test that proves the tests above can fail at all.

        A re-derivation that agreed with ``_ROWS`` no matter what the copy said
        would be the round-``uajlve`` defect one layer up: a check that asserts
        what the loader already guarantees.

        The forged value is derived from the real one rather than typed. The
        first version hardcoded ``"18990"``, which made this NEGATIVE CONTROL
        the thing that failed when a forgery happened to use the same number,
        and would fail spuriously the day the client ships it (pf-adversary,
        round i8timv, D11).
        """
        forged = copy_module.deepcopy(self.document)
        real = int(forged["marker_rows_verbatim"]["14"]["raw"]["n_Y"])
        forged["marker_rows_verbatim"]["14"]["raw"]["n_Y"] = str(real + 1)
        self.assertNotEqual(derive_rows(forged), world_scene_marker._ROWS)

    def test_forging_the_scene_index_in_the_copy_turns_this_file_red(self):
        forged = copy_module.deepcopy(self.document)
        for pair in forged["scene_marker_index"]:
            if pair[0] == 130:
                pair[1] = 130  # the shortcut, written into the data
        self.assertNotEqual(derive_rows(forged), world_scene_marker._ROWS)

    def test_the_copy_keeps_the_raw_unsigned_text_not_the_signed_reading(self):
        """Why the u32 reading is checked rather than assumed.

        The copy stores what the file stores.  Scene 1's ``n_X`` is
        ``4294956974`` there and ``-10322`` in the module, so a forger has to
        be consistent in a number system nobody reads by eye, and the
        conversion itself is exercised on real data every run.
        """
        raw_x = self.document["marker_rows_verbatim"]["1"]["raw"]["n_X"]
        self.assertEqual(raw_x, "4294956974")
        self.assertEqual(s32(raw_x), -10322)
        self.assertEqual(world_scene_marker._ROWS[0][3], s32(raw_x))

    def test_each_verbatim_row_agrees_with_the_index_at_its_own_line(self):
        """The two halves of the copy have to describe the same table.

        ``source_line`` is the row's 1-based line in the client's file (the
        header is line 1), so the marker index entry at that offset must be
        the same ``(n_ID, n_SCENE)`` pair the verbatim row carries.  A hand
        edit to one half and not the other dies here.
        """
        index = self.document["marker_scene_index"]
        for marker_id, entry in self.document["marker_rows_verbatim"].items():
            with self.subTest(marker=marker_id):
                pair = index[entry["source_line"] - 2]
                self.assertEqual(pair[0], int(entry["raw"]["n_ID"]))
                self.assertEqual(pair[1], int(entry["raw"]["n_SCENE"]))


class EveryTotalTheModuleStatesIsRecomputedTest(unittest.TestCase):
    """The six numbers a docstring got wrong by a factor of 36 (round 8ubiku).

    They were bridge-only before this round, which is how a wrong one survived
    to be committed.  The copy keeps ``(n_ID, n_MARKER)`` for all 271 scenes
    and ``(n_ID, n_SCENE)`` for all 390 markers -- two integers a row, no
    coordinates -- so every total is arithmetic the gate performs rather than
    a literal the gate reads.
    """

    def setUp(self):
        self.census = derive_census()

    def test_the_two_row_counts(self):
        self.assertEqual(self.census["scene_row_count"],
                         world_scene_marker.SCENE_ROW_COUNT)
        self.assertEqual(self.census["marker_row_count"],
                         world_scene_marker.MARKER_ROW_COUNT)

    def test_the_thirteen_scenes_that_name_a_marker(self):
        self.assertEqual(self.census["scenes_with_a_marker"],
                         world_scene_marker.SCENES_WITH_A_MARKER)

    def test_the_nineteen_self_numbered_marker_rows(self):
        self.assertEqual(
            self.census["marker_rows_whose_id_equals_their_scene"],
            world_scene_marker.MARKER_ROWS_WHOSE_ID_EQUALS_THEIR_SCENE,
        )

    def test_the_size_of_rule_2s_hazard(self):
        self.assertEqual(self.census["marker_less_scenes"],
                         world_scene_marker.MARKER_LESS_SCENES)
        self.assertEqual(
            self.census["scenes_the_shortcut_would_invent_a_point_for"],
            world_scene_marker.SCENES_THE_SHORTCUT_WOULD_INVENT_A_POINT_FOR,
        )
        self.assertEqual(
            self.census["shortcut_survives_the_back_pointer_check"],
            world_scene_marker.SHORTCUT_SURVIVES_THE_BACK_POINTER_CHECK,
        )

    def test_the_two_worked_examples_of_the_prohibition(self):
        self.assertEqual(
            self.census["marker_row_at_scene_130_belongs_to"],
            world_scene_marker.MARKER_ROW_AT_SCENE_130_BELONGS_TO,
        )
        self.assertEqual(world_marker_copy.shortcut_at_scene_17(),
                         world_scene_marker.SHORTCUT_AT_SCENE_17)

    def test_the_three_survivors_really_are_the_degenerate_origin(self):
        """The last sentence of the totals block that was only prose.

        ``world_scene_marker`` says markers 126/127/128 are "the degenerate
        (0, 0, z) origin". It was true and no machine could check it, because
        the copy kept no coordinates for those three (pf-adversary, round
        i8timv, D9). They are in the copy now.
        """
        derived = world_marker_copy.shortcut_survivor_points()
        self.assertEqual(derived, world_scene_marker.SHORTCUT_SURVIVOR_POINTS)
        self.assertEqual(
            tuple(point[0] for point in derived),
            world_scene_marker.SHORTCUT_SURVIVES_THE_BACK_POINTER_CHECK,
        )
        for marker_id, x, y, _z in derived:
            with self.subTest(marker=marker_id):
                self.assertEqual((x, y), (0, 0))


class TheReachStatementSaysWhatWasMeasuredTest(unittest.TestCase):
    """``VERIFICATION_REACH`` is the most-quoted string in this lane.

    Until this round it was also the least checked: the registry cites it as
    the authority on how far verification reaches and no test asserted a word
    of it, so the round that widened it shipped a claim its own adversary
    refuted in the same commit (pf-adversary, round i8timv, D3).
    """

    def test_it_does_not_claim_agreement_with_the_client(self):
        reach = world_scene_marker.VERIFICATION_REACH
        self.assertIn("NOT the merge gate", reach)
        self.assertIn("only where pf_bridge sits beside this repo", reach)

    def test_it_calls_the_copy_a_projection_rather_than_the_client_table(self):
        reach = world_scene_marker.VERIFICATION_REACH
        self.assertIn("CURATED PROJECTION", reach)

    def test_it_names_the_limit_the_adversary_measured(self):
        """The chain is written by one lane in one commit, and it says so."""
        reach = world_scene_marker.VERIFICATION_REACH
        self.assertIn("internally consistent", reach)
        self.assertIn("one commit", reach)

    def test_the_committed_copy_constant_names_a_file_that_exists(self):
        """``COMMITTED_COPY`` had no reader and no assertion (D10).

        A path constant nobody checks is the stale-pin shape this lane keeps
        writing up; rename the directory and it lies silently.
        """
        named = ROOT / world_scene_marker.COMMITTED_COPY
        self.assertTrue(named.is_file(), f"{named} does not exist")
        self.assertEqual(named.resolve(),
                         world_marker_copy.COPY_PATH.resolve())


class TheCopySaysWhereItCameFromAndWhoOwnsItTest(unittest.TestCase):
    """The ruling's third instruction: the rule lives in the file's header."""

    def setUp(self):
        self.document = load_copy()

    def test_both_full_sources_are_named_with_a_sha256(self):
        for key, path in (("scene_name", world_marker_copy.SCENE_NAME_TSV),
                          ("marker", world_marker_copy.MARKER_TSV)):
            with self.subTest(source=key):
                entry = self.document["source"][key]
                self.assertEqual(entry["path"], path)
                self.assertEqual(len(entry["sha256"]), 64)
                self.assertEqual(entry["sha256"], entry["sha256"].lower())
                int(entry["sha256"], 16)

    def test_the_source_row_counts_match_what_the_module_claims(self):
        self.assertEqual(self.document["source"]["scene_name"]["row_count"],
                         world_scene_marker.SCENE_ROW_COUNT)
        self.assertEqual(self.document["source"]["marker"]["row_count"],
                         world_scene_marker.MARKER_ROW_COUNT)

    def test_the_source_hashes_are_the_ones_world_scene_marker_pins(self):
        """One table's hash, two files.  They may not drift apart silently."""
        self.assertEqual(self.document["source"]["scene_name"]["sha256"],
                         world_scene_marker.SCENE_NAME_TSV_SHA256)
        self.assertEqual(self.document["source"]["marker"]["sha256"],
                         world_scene_marker.MARKER_TSV_SHA256)

    def test_the_header_says_who_updates_this_file_and_how(self):
        rule = self.document["_who_updates_this_and_when"]
        self.assertIn("LANE-A", rule)
        self.assertIn("regenerated, never hand-edited", rule)
        self.assertIn("COPY_SHA256", rule)
        self.assertIn("SAME", rule)

    def test_the_header_refuses_the_overclaim_before_anyone_makes_it(self):
        self.assertIn("does_not_prove", "".join(self.document.keys()))
        self.assertIn("bridge run", self.document["_what_it_does_not_prove"])


class TheseTestsRunOnEveryMachineTest(unittest.TestCase):
    """The ruling in force as arithmetic rather than as a sentence in a letter."""

    def test_this_file_never_learns_to_skip(self):
        """``COO-DECISION 20260829_0941``: this test may not skip.

        Read out of this file's own syntax tree rather than by grepping its
        text, so the check cannot be tripped by the words in a docstring and
        cannot be satisfied by renaming a decorator.  The failure mode it is
        here for is a future round hanging
        ``@BRIDGE_GAMEDATA.skip_unless_present()`` on a class to make a red go
        away -- which is exactly how the check this file replaces stopped
        running on the machine that gates the merge.
        """
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        # EVERY name and attribute in the module, lowercased.  The first
        # version of this test checked decorators (lowercased) plus two call
        # targets compared CASE-SENSITIVELY, and pf-adversary walked straight
        # through it three ways in round i8timv (D2): `raise
        # unittest.SkipTest(...)` has a capital S and was not matched; a skip
        # applied after the class body (`C = unittest.skip('later')(C)`) is an
        # Assign and has no decorator_list at all; and `__unittest_skip__ =
        # True` is neither. Scanning every Name/Attribute catches all three,
        # because a skip cannot be applied without naming something. Function
        # and class NAMES are not Name nodes, so this test's own name is fine,
        # and string literals are not either, so the prose above is fine.
        # IDENTIFIERS ONLY, not whole expressions.  Unparsing the node caught
        # `(ROOT / 'docs' / 'PYTEST_SKIP_PINS.json').read_text` because the
        # string literal is part of that expression - a check that cannot tell
        # a filename from a call would have forced the sibling test to stop
        # reading the pin file in order to stay green.
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifier = node.id
            elif isinstance(node, ast.Attribute):
                identifier = node.attr
            else:
                continue
            with self.subTest(identifier=identifier):
                self.assertNotIn(
                    "skip", identifier.lower(),
                    "this file may not name anything skip-shaped; "
                    "COO-DECISION 20260829_0941 says the re-derive test "
                    "runs on every machine",
                )

    def test_this_file_is_absent_from_every_section_of_the_skip_pin_file(self):
        """A file with no skips may not appear in the pin file at all.

        ``tools/pf_pytest_precondition_census.py`` goes red in either
        direction, so an entry added here later -- the paperwork half of
        adding a skip -- is caught even before the decorator is.

        Reads EVERY section, not just ``preconditions``: the first version
        read only that key, and ``design_skips`` is the other half of the
        file - pinning a bare ``SkipTest`` there was one of the three ways
        pf-adversary removed this file's guarantee with everything green
        (round i8timv, D2b).
        """
        pins = json.loads(
            (ROOT / "docs" / "PYTEST_SKIP_PINS.json").read_text(
                encoding="utf-8")
        )
        for section in ("preconditions", "design_skips"):
            with self.subTest(section=section):
                modules = [
                    entry.get("module") for entry in pins.get(section, [])
                ]
                self.assertNotIn("tests/test_world_marker_copy.py", modules)

    def test_the_load_bearing_test_is_still_here_under_its_own_name(self):
        """Deleting this file must not be a silent way to remove the check.

        pf-adversary deleted the whole module and the suite went green with a
        forged coordinate in place (round i8timv, D2a): nothing pinned that
        the file exists. The counterpart of this assertion lives in
        ``tests/test_world_scene_marker.py``, which re-derives ``_ROWS`` from
        the copy independently, so removing the guarantee now means deleting
        an assertion in a second file that names this one.
        """
        source = Path(__file__).read_text(encoding="utf-8")
        self.assertIn("def test_every_pinned_row_re_derives_from_the_copy",
                      source)


class TheReleaseArchiveConstraintTest(unittest.TestCase):
    """Why ``world_scene_marker`` keeps its literals instead of reading JSON.

    ``tools/build_foundation_release.py`` collects ``src/**/*.py`` and nothing
    else, so a module that read ``world_data/*.json`` at import would work
    here and die in the release archive.  That is a real constraint, not a
    style preference, and it is pinned so the next round that thinks "just
    load it at import" finds out in one second.
    """

    def test_the_release_archive_does_not_carry_this_data_file(self):
        """Executed against the builder, not asserted about its text.

        ~~``assertIn("(ROOT/'src').rglob('*.py')")`` plus
        ``assertNotIn("world_data")``~~ was here and did not test its own
        name: pf-adversary added ``rglob('*.json')`` to the builder and the
        test still passed, and the ``assertNotIn`` would also have fired on
        the FIX rather than only on the bug (round i8timv, D8). This imports
        the builder's own ``FILES`` list and asks it directly.
        """
        spec = importlib.util.spec_from_file_location(
            "pf_build_foundation_release",
            ROOT / "tools" / "build_foundation_release.py",
        )
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        collected = [Path(p) for p in builder.FILES]
        self.assertNotIn(world_marker_copy.COPY_PATH.resolve(),
                         [p.resolve() for p in collected])
        # And the reader itself DOES ship, which is the asymmetry worth
        # knowing: a release-side caller of load_copy() gets MarkerCopyError,
        # by design, rather than a wrong answer.
        self.assertIn(
            (ROOT / "src" / "pirateforce_foundation"
             / "world_marker_copy.py").resolve(),
            [p.resolve() for p in collected],
        )

    def test_no_module_in_the_package_imports_the_copy_reader(self):
        """Read as imports, not as text.

        The first draft of this test grepped for the module's name and went
        red on ``world_scene_marker.py``, which MENTIONS the copy in a comment
        that exists precisely to tell the next reader why it does not import
        it.  A test that cannot tell a citation from a dependency would have
        forced the explanation out of the file to stay green.
        """
        importers = []
        for path in sorted((ROOT / "src").rglob("*.py")):
            if path.name == "world_marker_copy.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""] + [
                        f"{node.module or ''}.{alias.name}"
                        for alias in node.names
                    ]
                else:
                    continue
                if any(name.endswith("world_marker_copy") for name in names):
                    importers.append(path.name)
                    break
        self.assertEqual(importers, [])


if __name__ == "__main__":
    unittest.main()
