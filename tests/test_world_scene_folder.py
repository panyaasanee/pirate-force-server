"""The gate-side half of COO-DECISION 20260829_0848 item 3: no skip, no bridge.

WHAT THESE TESTS ESTABLISH.  That ``world_scene_folder._FOLDER_BY_SCENE_ID``
is a faithful projection of ``world_data/world_scene_folder_crosswalk.json``,
that the copy's bytes are the bytes ``COPY_SHA256`` pins, that the addressed id
set is exactly the registry's, and that the reader is NOT ``model_id`` - the
defect the module exists to prevent, which is live for six of seventeen scenes.

WHAT THEY DO NOT ESTABLISH.  That the copy matches the client.  The client's
files are not in this repository; that hop is ``verify_against_sources()`` and
it is bridge-only, exercised from ``FolderReverificationOnTheBridgeTest``.
Same limit ``test_world_marker_copy`` states about itself, and it is stated
here rather than left to be assumed.

Every test in this file runs on every machine.  There is no skip decorator in
it except the one bridge-only case, and ``test_this_file_never_learns_to_skip``
fails if a later round adds another - the same lock round ``i8timv`` had to
build after pf-adversary walked three separate ways around a weaker version of
that check (raise SkipTest, a post-class decorator, a lowercase identifier).
"""

import ast
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_folder as wsf
from pirateforce_foundation import world_scene_numbering as wsn
from pirateforce_foundation import world_scene_marker

REGISTRY_PATH = ROOT / "scenarios" / "world_scene_registry_001.json"
BRIDGE_GAMEDATA = Path("/home/user/pf_bridge/gamedata")


def _registry_ids() -> tuple[int, ...]:
    document = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return tuple(int(row["n_id"]) for row in document["destinations"])


def _registry_model_ids() -> dict[int, str]:
    document = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {int(row["n_id"]): row["model_id"] for row in document["destinations"]}


class TheCopyIsThePinnedCopyTest(unittest.TestCase):

    def test_the_committed_bytes_are_the_pinned_bytes(self):
        document = wsf.load_copy()
        self.assertEqual(document["id"], "world_scene_folder_crosswalk_001")

    def test_a_copy_edited_without_moving_the_pin_is_refused(self):
        # The negative control for the lock.  Done by patching the constant
        # rather than by writing to the tree: a test that edits a committed
        # file leaves the repository dirty when it fails.
        original = wsf.COPY_SHA256
        wsf.COPY_SHA256 = "0" * 64
        try:
            with self.assertRaises(wsf.SceneFolderCopyError) as caught:
                wsf.load_copy()
        finally:
            wsf.COPY_SHA256 = original
        self.assertIn("sha256 mismatch", str(caught.exception))

    def test_a_missing_copy_is_an_error_and_not_an_empty_answer(self):
        original = wsf.COPY_PATH
        wsf.COPY_PATH = ROOT / "world_data" / "no_such_crosswalk.json"
        try:
            with self.assertRaises(wsf.SceneFolderCopyError):
                wsf.load_copy()
        finally:
            wsf.COPY_PATH = original


class TheLiteralsAreDerivedNotTypedTest(unittest.TestCase):

    def test_every_literal_row_re_derives_from_the_copy(self):
        ids = tuple(scene_id for scene_id, _ in wsf._FOLDER_BY_SCENE_ID)
        self.assertEqual(wsf.derive_folders(ids), wsf._FOLDER_BY_SCENE_ID)

    def test_the_public_reader_returns_the_table_for_every_addressed_id(self):
        """THE TEST THIS FILE WAS MISSING, AND IT WAS THE WHOLE POINT.

        Every other assertion here reads ``_FOLDER_BY_SCENE_ID`` directly, so
        they pin the TABLE and not the FUNCTION.  pf-adversary (round yam18f,
        D1) put an eleven-entry forgery dict inside ``scene_folder_for_scene_id``
        - covering 5, 6, 7, 8, 9, 10, 11, 17, 130, 278, 997, two of them among
        the six the module's whole thesis is about - and the suite stayed green
        at 24 passed.  The reader is what runtime.py will call; a table nobody
        reads through is not a guarantee.
        """
        for scene_id, folder in wsf._FOLDER_BY_SCENE_ID:
            with self.subTest(scene_id=scene_id):
                self.assertEqual(wsf.scene_folder_for_scene_id(scene_id),
                                 folder)

    def test_the_console_token_reads_through_the_reader_for_every_id(self):
        # Same hole, one layer up: the greppable proof token printed at boot
        # was compared against nothing, so addressed=1 fired for a forged
        # spelling exactly as it does for a right one.
        for scene_id, folder in wsf._FOLDER_BY_SCENE_ID:
            with self.subTest(scene_id=scene_id):
                self.assertEqual(
                    wsf.folder_console_suffix(scene_id),
                    "WORLD_SCENE_FOLDER scene_id=%d folder=%s addressed=1"
                    % (scene_id, folder))

    def test_the_source_digests_are_pinned_and_shared_with_the_marker_module(self):
        # Without this the copy names which FILES it came from, not which
        # CLIENT BUILD: a regeneration against a patched client re-pins
        # COPY_SHA256, updates the literals, and passes everything while this
        # module and world_scene_marker describe two different clients
        # (pf-adversary, round yam18f, D5).  The two modules read the SAME
        # scene table, so their pins must agree.
        provenance = wsf.load_copy()["provenance"]
        self.assertEqual(provenance["scene_name_table_sha256"],
                         wsf.SCENE_NAME_TSV_SHA256)
        self.assertEqual(provenance["scene_index_sha256"],
                         wsf.SCENE_INDEX_TSV_SHA256)
        self.assertEqual(wsf.SCENE_NAME_TSV_SHA256,
                         world_scene_marker.SCENE_NAME_TSV_SHA256)
        self.assertEqual(wsf.SCENE_NAME_TSV, world_scene_marker.SCENE_NAME_TSV)

    def test_the_addressed_ids_are_exactly_the_registrys(self):
        # This is what keeps the module from becoming the second table the COO
        # said not to build: a destination added to the registry with no
        # address here goes red, and an address here for a scene the registry
        # does not carry goes red too.
        self.assertEqual(
            sorted(scene_id for scene_id, _ in wsf._FOLDER_BY_SCENE_ID),
            sorted(_registry_ids()),
        )

    def test_the_totals_this_module_states_re_derive_from_the_copy(self):
        totals = wsf.derive_totals()
        self.assertEqual(totals["scene_row_count"], wsf.CLIENT_SCENE_ROW_COUNT)
        self.assertEqual(totals["spelling_mismatch_count"],
                         wsf.CLIENT_SPELLING_MISMATCH_COUNT)
        self.assertEqual(totals["distinct_folders_named_by_a_scene"],
                         wsf.CLIENT_DISTINCT_FOLDERS_NAMED_BY_A_SCENE)
        self.assertEqual(totals["folders_named_by_more_than_one_scene"],
                         wsf.FOLDERS_NAMED_BY_MORE_THAN_ONE_SCENE)

    def test_the_two_folder_counts_are_not_the_same_quantity(self):
        # An earlier draft of the module used one key name for both, computing
        # 226 under a name the copy uses for 289.  Pin them apart so a later
        # round cannot quietly re-merge them.
        self.assertNotEqual(wsf.CLIENT_SCENE_FOLDER_COUNT,
                            wsf.CLIENT_DISTINCT_FOLDERS_NAMED_BY_A_SCENE)
        # Both COMPUTED from the copy's data, not read from the copy's own
        # totals block.  Until this round's adversary pass (D6) the 289 was
        # compared against its own transcription, which is the thing
        # derive_totals' docstring says is not a check.
        totals = wsf.derive_totals()
        self.assertEqual(totals["scene_folders_shipped_by_the_index"],
                         wsf.CLIENT_SCENE_FOLDER_COUNT)
        self.assertEqual(totals["distinct_folders_named_by_a_scene"],
                         wsf.CLIENT_DISTINCT_FOLDERS_NAMED_BY_A_SCENE)

    def test_case_uniqueness_is_computed_from_the_folder_list_not_declared(self):
        # It was a bare `True` whose only test asserted True is True - a claim
        # about the client nothing on the gate could falsify (D6).  The copy
        # now carries the index's 289 folder names, so the join's founding
        # assumption is arithmetic here.
        self.assertTrue(wsf.folder_names_are_case_unique())
        document = wsf.load_copy()
        self.assertEqual(len(document["index_folder_names"]),
                         wsf.CLIENT_SCENE_FOLDER_COUNT)
        forged = dict(document)
        forged["index_folder_names"] = ["bg0001", "BG0001"]
        self.assertFalse(wsf.folder_names_are_case_unique(forged))

    def test_every_folder_a_scene_names_is_one_the_index_ships(self):
        document = wsf.load_copy()
        shipped = set(document["index_folder_names"])
        named = {folder for _, folder in document["scene_folder_index"]}
        self.assertTrue(named <= shipped)
        self.assertEqual(len(named),
                         wsf.CLIENT_DISTINCT_FOLDERS_NAMED_BY_A_SCENE)


class TheReaderIsNotModelIdTest(unittest.TestCase):
    """The defect this module exists to prevent, pinned so it cannot return."""

    def test_six_addressed_scenes_disagree_with_their_model_id(self):
        models = _registry_model_ids()
        differing = tuple(sorted(
            scene_id for scene_id, folder in wsf._FOLDER_BY_SCENE_ID
            if models[scene_id] != folder
        ))
        self.assertEqual(differing, wsf.SPELLING_DIFFERS_FROM_MODEL_ID)
        # Not merely "different": say which way, so the test documents the
        # answer a caller gets wrong.
        self.assertEqual(models[1], "BG0001")
        self.assertEqual(wsf.scene_folder_for_scene_id(1), "bg0001")
        self.assertEqual(models[2], "BG0002")
        self.assertEqual(wsf.scene_folder_for_scene_id(2), "Bg0002")

    def test_no_single_case_transform_reproduces_the_client_spellings(self):
        # Scene 3 is Bg0003 and scene 4 is bg0004, from model ids that differ
        # only in the same way.  So the two obvious repairs each fix some rows
        # and break others, which is the case for reading a table rather than
        # transforming a string.  Stated as the measurement rather than as
        # "no rule works": lower() IS right for scene 4.
        self.assertEqual(wsf.scene_folder_for_scene_id(3), "Bg0003")
        self.assertEqual(wsf.scene_folder_for_scene_id(4), "bg0004")
        models = _registry_model_ids()
        lower_is_right = tuple(sorted(
            scene_id for scene_id, folder in wsf._FOLDER_BY_SCENE_ID
            if models[scene_id].lower() == folder
        ))
        lower_is_wrong = tuple(sorted(
            scene_id for scene_id, folder in wsf._FOLDER_BY_SCENE_ID
            if models[scene_id].lower() != folder
        ))
        self.assertEqual(lower_is_right, (1, 4, 5, 6))
        self.assertEqual(
            lower_is_wrong,
            (2, 3, 7, 8, 9, 10, 11, 14, 17, 126, 130, 278, 997))
        # And the verbatim model id is wrong for the six the module names.
        verbatim_is_wrong = tuple(sorted(
            scene_id for scene_id, folder in wsf._FOLDER_BY_SCENE_ID
            if models[scene_id] != folder
        ))
        self.assertEqual(verbatim_is_wrong, wsf.SPELLING_DIFFERS_FROM_MODEL_ID)

    def test_the_answer_is_what_the_numbering_guard_is_keyed_by(self):
        # The independent, hand-typed source already on main.  It carries three
        # anchors and two of them are case-different from model_id, so this is
        # a real cross-check rather than a restatement: if the reader returned
        # model_id, two of these three would fail.
        for scene_id, expected in wsn.SCENE_ID_TO_SCENE_FILE.items():
            self.assertEqual(wsf.scene_folder_for_scene_id(scene_id), expected)

    def test_the_owner_confirmed_scene_stays_confirmed_through_the_reader(self):
        # The consequence, driven rather than described: feed the reader's
        # answer to the guard the chief's roster path will consult.  With
        # model_id in its place this returns False for the one scene whose cast
        # the owner walked and confirmed on screen.
        folder = wsf.scene_folder_for_scene_id(2)
        self.assertTrue(wsn.identity_is_provable(folder))
        self.assertIsNone(wsn.identity_block_reason(folder))
        models = _registry_model_ids()
        self.assertFalse(wsn.identity_is_provable(models[2]))


class TheReaderRefusesRatherThanGuessesTest(unittest.TestCase):

    def test_an_unaddressed_scene_id_is_None_and_not_a_fallback(self):
        # 186 is the sharpest case available: it is a real client scene whose
        # folder the copy knows (Bg1001), and the reader still refuses it,
        # because this registry has never vetted it.
        self.assertIsNone(wsf.scene_folder_for_scene_id(186))
        folder_by_id = {int(n): f for n, f
                        in wsf.load_copy()["scene_folder_index"]}
        self.assertEqual(folder_by_id[186], "Bg1001")

    def test_a_non_integer_scene_id_raises_rather_than_answering(self):
        for bad in ("1", 1.0, None, True, False, b"1"):
            with self.assertRaises(ValueError):
                wsf.scene_folder_for_scene_id(bad)

    def test_None_stops_being_a_refusal_one_call_downstream(self):
        """The hazard, recorded rather than asserted away.

        The module says ``None`` is an answer.  It is - for exactly one call.
        Feed it to the guard this package composes it with and an unaddressed
        scene, a nonexistent scene and an addressed-but-unconfirmed scene
        produce byte-identical verdicts (pf-adversary, round yam18f, D9).  This
        test exists so that stays visible: if a later round makes the refusal
        distinguishable downstream, this goes red and the round has to say so
        rather than quietly changing what ``None`` means to a caller.
        """
        verdicts = {}
        for scene_id in (4242, 186, 17):
            folder = wsf.scene_folder_for_scene_id(scene_id)
            verdicts[scene_id] = (wsn.identity_is_provable(folder),
                                  wsn.identity_block_reason(folder))
        self.assertEqual(verdicts[4242], verdicts[186])
        self.assertEqual(verdicts[186], verdicts[17])
        self.assertFalse(verdicts[17][0])
        # The ONLY signal that separates them is the reader's own token.
        self.assertIn("addressed=0", wsf.folder_console_suffix(186))
        self.assertIn("addressed=1", wsf.folder_console_suffix(17))

    def test_the_console_token_is_ascii_and_names_an_unaddressed_scene(self):
        # The bridge console is cp874.
        for scene_id in (1, 14, 186, 4242):
            line = wsf.folder_console_suffix(scene_id)
            line.encode("ascii")
            line.encode("cp874")
        self.assertIn("folder=?", wsf.folder_console_suffix(4242))
        self.assertIn("addressed=0", wsf.folder_console_suffix(4242))
        self.assertIn("folder=Bg0015", wsf.folder_console_suffix(14))


class TheInverseIsNotAFunctionTest(unittest.TestCase):

    def test_scene_17_and_186_share_a_folder_and_that_is_recorded(self):
        document = wsf.load_copy()
        sharing = {folder: tuple(ids)
                   for folder, ids in document["scene_ids_sharing_a_folder"]}
        self.assertEqual(sharing["Bg1001"], (17, 186))
        self.assertEqual(wsf.SCENE_IDS_SHARING_AN_ADDRESSED_FOLDER,
                         ((17, 186, "Bg1001"),))

    def test_only_one_sharing_pair_touches_an_addressed_scene_today(self):
        # The day a round addresses 186 - or any other second id of a sharing
        # pair - this goes red, which is the point: it is a decision, not a
        # side effect.
        document = wsf.load_copy()
        addressed = set(_registry_ids())
        touched = sorted(
            (folder, tuple(ids))
            for folder, ids in document["scene_ids_sharing_a_folder"]
            if addressed & set(ids)
        )
        self.assertEqual(touched, [("Bg1001", (17, 186))])
        self.assertEqual(len(addressed & {186}), 0)


class TheCopyIsInternallyConsistentTest(unittest.TestCase):

    def test_every_row_folder_matches_its_model_id_case_insensitively(self):
        document = wsf.load_copy()
        models = {int(n): m for n, m in document["scene_model_index"]}
        folders = {int(n): f for n, f in document["scene_folder_index"]}
        self.assertEqual(sorted(models), sorted(folders))
        for scene_id, folder in folders.items():
            self.assertEqual(folder.lower(), models[scene_id].lower())

    def test_the_recorded_mismatches_are_exactly_the_rows_that_differ(self):
        document = wsf.load_copy()
        models = {int(n): m for n, m in document["scene_model_index"]}
        folders = {int(n): f for n, f in document["scene_folder_index"]}
        computed = sorted(scene_id for scene_id in folders
                          if folders[scene_id] != models[scene_id])
        recorded = sorted(int(row[0])
                          for row in document["spelling_mismatches"])
        self.assertEqual(computed, recorded)
        self.assertEqual(len(recorded), wsf.CLIENT_SPELLING_MISMATCH_COUNT)

    def test_the_copy_names_the_sources_it_was_built_from(self):
        provenance = wsf.load_copy()["provenance"]
        self.assertEqual(provenance["scene_name_table"], wsf.SCENE_NAME_TSV)
        self.assertEqual(provenance["scene_index"], wsf.SCENE_INDEX_TSV)
        for key in ("scene_name_table_sha256", "scene_index_sha256"):
            self.assertRegex(provenance[key], r"^[0-9a-f]{64}$")


class TheGeneratorRefusesAnAmbiguousJoinTest(unittest.TestCase):

    def _tsv(self, directory, rows, name, subdir=None):
        target = directory / subdir if subdir else directory
        target.mkdir(parents=True, exist_ok=True)
        path = target / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            handle.write("\n".join("\t".join(row) for row in rows) + "\n")
        return path

    def test_two_folders_differing_only_by_case_are_refused(self):
        # FOLDER_NAMES_ARE_CASE_UNIQUE is the assumption the whole join rests
        # on.  Today's client satisfies it (289 of 289 distinct when lowered);
        # this drives what happens when a future one does not, so the answer is
        # a refusal rather than whichever row came last.
        import tempfile
        with tempfile.TemporaryDirectory() as raw:
            gamedata = Path(raw)
            self._tsv(gamedata,
                      [("n_ID", "s_MODLE_ID"), ("1", "BG0001")],
                      "CONSTDATA_TH__SCENE_NAME.tsv", subdir="tables")
            self._tsv(gamedata,
                      [("scene",), ("bg0001",), ("BG0001",)],
                      "PF_GAMEDATA_SCENE_INDEX.tsv")
            with self.assertRaises(wsf.SceneFolderCopyError) as caught:
                wsf.curate(gamedata)
        self.assertIn("differ", str(caught.exception))
        self.assertIn("no longer a function", str(caught.exception))

    def test_a_scene_whose_model_has_no_folder_is_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as raw:
            gamedata = Path(raw)
            self._tsv(gamedata,
                      [("n_ID", "s_MODLE_ID"), ("1", "BG0001"),
                       ("2", "BgGhost")],
                      "CONSTDATA_TH__SCENE_NAME.tsv", subdir="tables")
            self._tsv(gamedata, [("scene",), ("bg0001",)],
                      "PF_GAMEDATA_SCENE_INDEX.tsv")
            with self.assertRaises(wsf.SceneFolderCopyError) as caught:
                wsf.curate(gamedata)
        # Matched on wording unique to THIS refusal.  The first version
        # asserted "no " appears, which the case-collision message also
        # contains ("no longer a function") - a test that could not tell the
        # two refusals apart (pf-adversary, round yam18f, D7).
        self.assertIn("has no folder", str(caught.exception))
        self.assertIn("BgGhost", str(caught.exception))

    def test_a_duplicate_scene_id_is_refused(self):
        # The folder side of the join was guarded from the first draft; the
        # scene side was not, so a client shipping n_ID twice resolved to
        # whichever row came last, silently, with every test green (D7).
        import tempfile
        with tempfile.TemporaryDirectory() as raw:
            gamedata = Path(raw)
            self._tsv(gamedata,
                      [("n_ID", "s_MODLE_ID"), ("2", "Bg0002"),
                       ("2", "Bg0003")],
                      "CONSTDATA_TH__SCENE_NAME.tsv", subdir="tables")
            self._tsv(gamedata, [("scene",), ("Bg0002",), ("Bg0003",)],
                      "PF_GAMEDATA_SCENE_INDEX.tsv")
            with self.assertRaises(wsf.SceneFolderCopyError) as caught:
                wsf.curate(gamedata)
        self.assertIn("appears twice", str(caught.exception))


class ThisFileCannotLearnToSkipTest(unittest.TestCase):
    """No test in this file may skip on any machine, including the gate.

    ROUND ``yam18f`` REWROTE THIS AFTER pf-adversary WALKED IT THREE WAYS (D2),
    and the first draft's own docstring claimed it had been "copied whole" from
    ``test_world_marker_copy.py`` when it had not been.  What it had instead
    were two exemptions the precedent does not have:

    * a whitelist for ``skip_unless_bridge_gamedata``, which NOTHING IN THE
      FILE EVER DEFINED OR USED - a pre-authorized skip decorator waiting for
      someone to define it.  Defining it as a two-line wrapper skipped both
      substantive classes with this lock still green (16 passed, 8 skipped).
    * an exemption for any identifier containing ``never_learns_to_skip``,
      which an import alias could simply be named after (20 passed, 4 skipped).

    Both were removed and the file still passes, so neither was ever needed:
    function and class NAMES are not ``Name`` nodes, which is exactly what the
    precedent's comment says.  ``ast.alias`` is now walked too - the third
    walkaround was ``from unittest import SkipTest as _Bail``, where the name
    ``SkipTest`` lives on an ``alias`` node the old scan never visited.
    """

    def test_this_file_never_learns_to_skip(self):
        source = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifier = node.id
            elif isinstance(node, ast.Attribute):
                identifier = node.attr
            elif isinstance(node, ast.alias):
                # Both halves: `import x as skipper` and `from m import skip`.
                identifier = "%s %s" % (node.name, node.asname or "")
            else:
                continue
            with self.subTest(identifier=identifier):
                self.assertNotIn(
                    "skip", identifier.lower(),
                    "this file may not name anything skip-shaped; the "
                    "bridge-only hop lives in "
                    "tests/test_world_scene_folder_on_the_bridge.py, which is "
                    "pinned in docs/PYTEST_SKIP_PINS.json",
                )

    def test_this_file_is_absent_from_every_section_of_the_skip_pin_file(self):
        """A file with no skips may not appear in the pin file at all.

        Compares the ``module`` FIELDS rather than searching the raw text, the
        way the precedent does.  A raw substring search cannot tell a pin from
        prose: the sibling entry for
        ``tests/test_world_scene_folder_on_the_bridge.py`` explains itself by
        naming this file in its note, and a text search calls that a pin.
        """
        pins_path = ROOT / "docs" / "PYTEST_SKIP_PINS.json"
        self.assertTrue(pins_path.exists(),
                        "the skip-pins file this check reads is missing")
        pins = json.loads(pins_path.read_text(encoding="utf-8"))
        for section in ("preconditions", "design_skips"):
            with self.subTest(section=section):
                modules = [entry.get("module")
                           for entry in pins.get(section, [])]
                self.assertNotIn("tests/test_world_scene_folder.py", modules)
        # And the bridge-only sibling MUST be pinned, in the same commit.
        pinned = [entry.get("module") for entry in pins.get("preconditions", [])]
        self.assertIn("tests/test_world_scene_folder_on_the_bridge.py", pinned)

    def test_the_load_bearing_test_file_is_still_here_under_its_own_name(self):
        """The precedent's third test, which the first draft claimed to have
        copied and did not (pf-adversary, round yam18f, D3).

        Deleting ``tests/test_world_scene_folder.py`` outright and forging the
        literals ran the WHOLE suite green - 4459 passed, 0 failed - because
        nothing anywhere else in the tree named this module.  The counterpart
        of this assertion lives in ``tests/test_world_scene_numbering.py``, a
        file this one cannot delete without that one going red.
        """
        self.assertTrue((ROOT / "tests" / "test_world_scene_folder.py").exists())
        counterpart = (ROOT / "tests" / "test_world_scene_numbering.py")
        self.assertIn("world_scene_folder",
                      counterpart.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
