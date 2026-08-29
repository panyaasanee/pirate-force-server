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

    def test_all_thirteen_rows_and_all_seven_columns_are_covered(self):
        """A projection over 12 of 13 rows would pass the test above.

        It would not: the tuples are compared whole.  This states the size of
        what that comparison covers so a later round that narrows the copy
        finds out here rather than in a docstring.
        """
        derived = derive_rows(self.document)
        self.assertEqual(len(derived), world_scene_marker.SCENES_WITH_A_MARKER)
        self.assertTrue(all(len(row) == 7 for row in derived))

    def test_forging_a_coordinate_in_the_copy_turns_this_file_red(self):
        """The test that proves the tests above can fail at all.

        A re-derivation that agreed with ``_ROWS`` no matter what the copy said
        would be the round-``uajlve`` defect one layer up: a check that asserts
        what the loader already guarantees.
        """
        forged = copy_module.deepcopy(self.document)
        forged["marker_rows_verbatim"]["14"]["raw"]["n_Y"] = "18990"
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
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                for decorator in node.decorator_list:
                    with self.subTest(decorated=node.name):
                        self.assertNotIn(
                            "skip", ast.unparse(decorator).lower(),
                            f"{node.name} grew a skip decorator; the ruling "
                            "says this file runs on every machine",
                        )
            if isinstance(node, ast.Call):
                target = ast.unparse(node.func)
                with self.subTest(call=target):
                    self.assertNotIn("skipTest", target)
                    self.assertNotIn("skip_unless_present", target)

    def test_this_file_is_absent_from_the_skip_pin_census(self):
        """A file with no skips may not appear in the pin file at all.

        ``tools/pf_pytest_precondition_census.py`` goes red in either
        direction, so an entry added here later -- the paperwork half of
        adding a skip -- is caught even before the decorator is.
        """
        pins = json.loads(
            (ROOT / "docs" / "PYTEST_SKIP_PINS.json").read_text(
                encoding="utf-8")
        )
        modules = [entry["module"] for entry in pins["preconditions"]]
        self.assertNotIn("tests/test_world_marker_copy.py", modules)


class TheReleaseArchiveConstraintTest(unittest.TestCase):
    """Why ``world_scene_marker`` keeps its literals instead of reading JSON.

    ``tools/build_foundation_release.py`` collects ``src/**/*.py`` and nothing
    else, so a module that read ``world_data/*.json`` at import would work
    here and die in the release archive.  That is a real constraint, not a
    style preference, and it is pinned so the next round that thinks "just
    load it at import" finds out in one second.
    """

    def test_the_release_archive_still_collects_only_python_from_src(self):
        builder = (ROOT / "tools" / "build_foundation_release.py").read_text(
            encoding="utf-8")
        self.assertIn("(ROOT/'src').rglob('*.py')", builder)
        self.assertNotIn("world_data", builder)

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
