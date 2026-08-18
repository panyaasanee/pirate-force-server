"""SCAN-DEBT-001 - one definition of "a client UI model file", used by both sides.

``PF_SPLIT_OPERATE003``'s caption route is closed by a NEGATIVE: no ``.model``
file in the client's UI model directory is named split or divide.  Until round 84
that negative was computed over two different sets - the tool listed the whole
directory (573 entries) and the regression test globbed ``*.model`` (534 files) -
so the tool and the test that guards it were not measuring the same thing.  Both
now call ``tools/pf_client_ui_assets``.

This file is deliberately pure stdlib.  ``tests/test_split_operate_verb_panels_static.py``
imports ``pefile`` and ``capstone`` and therefore cannot even be collected in the
gate environment, which is precisely why the shared counter needs a guard that
can run there.  Every trap builds a throwaway tree under a temporary directory;
nothing here touches the real client assets, ``evidence/``, ``capture_v141/``,
``references/`` or ``state/``.

Run just this file:
    python3 -m pytest tests/test_client_ui_asset_inventory.py -q
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.pf_client_ui_assets import (
    DEFAULT_MODEL_DIR,
    ClientAssetsUnavailable,
    model_files,
    model_names,
    models_named,
)

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "pf_split_operate_verb_panels_static.py"
SIBLING_TEST = ROOT / "tests" / "test_split_operate_verb_panels_static.py"


def _fake_model_dir(root: Path) -> Path:
    """A directory shaped like the real one: models, sidecars and a subdirectory."""
    directory = root / "Model"
    directory.mkdir()
    for name in ("Common_NumInput.model", "Common_NumberInput2.model",
                 "Common_NumberInput3.model"):
        (directory / name).write_bytes(b"\xef\xbb\xbf<UIControlData></UIControlData>")
    (directory / "Common_NumInput.project").write_bytes(b"editor sidecar")
    (directory / "Layout.fsl").write_bytes(b"sidecar")
    (directory / "Hints.tip").write_bytes(b"sidecar")
    (directory / "Nested.model").mkdir()  # a DIRECTORY whose name ends in .model
    return directory


class DefinitionTests(unittest.TestCase):
    """What counts, what does not, and why - asserted rather than assumed."""

    def test_only_model_files_count(self):
        with TemporaryDirectory() as tmp:
            directory = _fake_model_dir(Path(tmp))
            self.assertEqual(
                model_names(directory),
                {"common_numinput.model", "common_numberinput2.model",
                 "common_numberinput3.model"})

    def test_editor_sidecars_are_excluded(self):
        with TemporaryDirectory() as tmp:
            directory = _fake_model_dir(Path(tmp))
            names = model_names(directory)
            self.assertNotIn("common_numinput.project", names)
            self.assertNotIn("layout.fsl", names)
            self.assertNotIn("hints.tip", names)
            # The whole-directory count is the number the old tool used.
            self.assertEqual(len(list(directory.iterdir())), 7)
            self.assertEqual(len(names), 3)

    def test_a_directory_named_like_a_model_is_not_a_model(self):
        with TemporaryDirectory() as tmp:
            directory = _fake_model_dir(Path(tmp))
            self.assertNotIn("nested.model", model_names(directory))

    def test_the_extension_match_is_case_insensitive(self):
        # glob("*.model") is case-sensitive on Linux and case-insensitive on
        # Windows.  A negative that means two different things on the gate box
        # and the commit box is not a negative.
        with TemporaryDirectory() as tmp:
            directory = _fake_model_dir(Path(tmp))
            (directory / "Shouty.MODEL").write_bytes(b"<UIControlData/>")
            self.assertIn("shouty.model", model_names(directory))

    def test_models_named_reports_the_offenders_not_a_boolean(self):
        with TemporaryDirectory() as tmp:
            directory = _fake_model_dir(Path(tmp))
            self.assertEqual(models_named(("split", "divide"), directory), [])
            (directory / "Inventory_SplitStack.model").write_bytes(b"<UIControlData/>")
            self.assertEqual(models_named(("split", "divide"), directory),
                             ["inventory_splitstack.model"])


class TrapTests(unittest.TestCase):
    """A guard that cannot fail is not a guard."""

    def test_a_missing_directory_raises_instead_of_answering_empty(self):
        with TemporaryDirectory() as tmp:
            missing = Path(tmp) / "there-is-no-Model-dir"
            with self.assertRaises(ClientAssetsUnavailable) as caught:
                model_files(missing)
            self.assertIn("FAILURE to verify", str(caught.exception))

    def test_a_file_where_the_directory_should_be_raises(self):
        with TemporaryDirectory() as tmp:
            impostor = Path(tmp) / "Model"
            impostor.write_bytes(b"not a directory")
            with self.assertRaises(ClientAssetsUnavailable):
                model_files(impostor)

    def test_an_empty_directory_is_an_answer_and_a_missing_one_is_not(self):
        with TemporaryDirectory() as tmp:
            empty = Path(tmp) / "Model"
            empty.mkdir()
            self.assertEqual(model_files(empty), [])          # looked, found none
            with self.assertRaises(ClientAssetsUnavailable):  # could not look
                model_files(Path(tmp) / "gone")

    def test_a_split_named_model_would_break_the_published_negative(self):
        """If the client ever shipped one, PF_SPLIT_OPERATE003's R2 is wrong."""
        with TemporaryDirectory() as tmp:
            directory = _fake_model_dir(Path(tmp))
            (directory / "Common_DivideItem.model").write_bytes(b"<UIControlData/>")
            self.assertNotEqual(models_named(("split", "divide"), directory), [])


class SharedCounterTests(unittest.TestCase):
    """The tool and its regression test must not grow private counters again."""

    def _imports_shared_counter(self, path: Path) -> bool:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and \
                    node.module.endswith("pf_client_ui_assets"):
                return True
        return False

    def test_both_sides_import_the_shared_counter(self):
        for path in (TOOL, SIBLING_TEST):
            with self.subTest(path=path.name):
                self.assertTrue(self._imports_shared_counter(path), path)

    def test_neither_side_builds_its_own_model_set(self):
        for path in (TOOL, SIBLING_TEST):
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn("os.listdir(GUI_MODEL)", source)
                self.assertNotIn('GUI_MODEL.glob("*.model")', source)

    def test_the_tool_no_longer_skips_when_the_assets_are_missing(self):
        tree = ast.parse(TOOL.read_text(encoding="utf-8"))
        printed = [
            argument.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name) and node.func.id == "print"
            for argument in node.args
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
            and "SKIP" in argument.value
        ]
        self.assertEqual(printed, [])


class RealAssetTests(unittest.TestCase):
    """The live numbers, so the definition is anchored to something real."""

    def setUp(self):
        if not DEFAULT_MODEL_DIR.is_dir():
            # Not a skip-as-escape-hatch: this class asserts facts about the game
            # install tree, which is legitimately absent on a machine that has
            # only the repository.  Every guard that MATTERS is above and runs
            # on a throwaway tree.
            self.skipTest("game install tree not present beside the repository")

    def test_the_two_old_denominators_really_did_differ(self):
        whole_directory = len(list(DEFAULT_MODEL_DIR.iterdir()))
        models = len(model_files(DEFAULT_MODEL_DIR))
        self.assertGreater(whole_directory, models,
                           "the sidecars that made 573 != 534 are gone; if so, "
                           "re-read tools/pf_client_ui_assets.__doc__ before "
                           "deleting anything")

    def test_the_published_negative_still_holds(self):
        self.assertEqual(models_named(("split", "divide"), DEFAULT_MODEL_DIR), [])
        self.assertIn("common_numinput.model", model_names(DEFAULT_MODEL_DIR))


if __name__ == "__main__":
    unittest.main()
