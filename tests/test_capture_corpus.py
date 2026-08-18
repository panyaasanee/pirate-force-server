"""CORPUS-PIN-001 - enforce docs/PF_CAPTURE_CORPUS.json as the single home for
*which capture files are evidence*.

Background (round 82).  Static verifiers used to decide which captures they were
allowed to quote by scanning a directory, and then pinned the resulting NUMBER
into a published report.  A headless replay job that booted the server without
``--capture-root`` wrote fresh captures into the golden corpus; because
``capture_v141/`` is git-ignored, nothing in the gate went red.  The corpus grew
69 -> 72 and the only symptom was a count owned by an unrelated milestone, found
by accident.

These tests exist so that the fix survives whoever is at the keyboard:

  * every pinned capture must be present and byte-identical (content, not just
    a count);
  * the capture directories must hold NO capture outside the pinned set - this
    is the guard that turns the incident above into an immediate red;
  * the two live files the old glob swept up (``GAME_LIVE.txt``,
    ``GAME_EVENTS_LIVE.txt``) must be excluded BY NAME, with a reason, so that
    dropping them stays a recorded decision and cannot be quietly widened into
    "ignore anything inconvenient".

The stray-detection test does not write into the real corpus.  It builds a
throwaway tree, copies the set definition onto it, and proves that a single
unexpected file is enough to raise.

These tests open no socket, touch no database and launch no GameClient.

Run just this file:
    python3 -m pytest tests/test_capture_corpus.py -q
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.pf_capture_corpus import (
    DEFAULT_TABLE,
    ROOT,
    CaptureCorpus,
    CaptureCorpusError,
    CaptureSet,
    sha256_of,
)

# The two files the pre-CORPUS-PIN-001 glob counted as evidence and should not
# have: the server truncates and rewrites both on every run.
LIVE_FILES = {
    "capture_v141/GAME_LIVE.txt",
    "capture_v141/GAME_EVENTS_LIVE.txt",
}

FIX_HINT = (
    "If this is red because an unexpected capture appeared, DO NOT run "
    "--regenerate to make it green: find the job that wrote into the corpus "
    "and give it an explicit --capture-root outside the repository."
)


class CaptureCorpusTableTests(unittest.TestCase):
    """The table itself is well formed."""

    def setUp(self) -> None:
        self.raw = json.loads(DEFAULT_TABLE.read_text(encoding="utf-8"))
        self.corpus = CaptureCorpus.load()

    def test_table_is_tracked_in_docs(self) -> None:
        # /docs/ is allow-listed in .gitignore; the capture directories are not.
        # This file is the only part of the evidence story git can diff.
        self.assertEqual(DEFAULT_TABLE.parent.name, "docs")
        self.assertTrue(DEFAULT_TABLE.is_file())

    def test_table_explains_itself(self) -> None:
        doc = "\n".join(self.raw["__doc__"])
        for needle in ("SINGLE SOURCE OF TRUTH", "--capture-root",
                       "assert_no_strays", "regenerate"):
            self.assertIn(needle, doc,
                          "the table's own header must explain %r" % needle)

    def test_every_expected_set_is_declared(self) -> None:
        # An exact list on purpose: admitting a set is a deliberate act and has
        # to be visible in a diff of this test as well as of the table.
        # game_teleportcheck_0x4477 was added in round 84 (SCAN-DEBT-001) when
        # tools/pf_teleportcheck_0x4477_static.py stopped globbing the game
        # install tree and started reading the pinned corpus instead.
        self.assertEqual(sorted(self.corpus.sets),
                         ["game_teleportcheck_0x4477",
                          "game_v141_archived",
                          "login_archived"])

    def test_every_set_says_where_it_looks(self) -> None:
        for name, spec in sorted(self.raw["sets"].items()):
            with self.subTest(set=name):
                self.assertEqual(
                    ("scan_dir" in spec) != ("scan_dirs" in spec), True,
                    "set %r must declare exactly one of scan_dir / scan_dirs" % name)

    def test_entries_are_well_formed(self) -> None:
        for name, holder in sorted(self.corpus.sets.items()):
            with self.subTest(set=name):
                paths = holder.relative_paths
                self.assertTrue(paths, "set %r is empty" % name)
                self.assertEqual(len(paths), len(set(paths)),
                                 "duplicate path in set %r" % name)
                self.assertEqual(paths, sorted(paths),
                                 "set %r must stay sorted so diffs are readable"
                                 % name)
                self.assertEqual(len(paths), self.raw["sets"][name]["file_count"])
                for entry in holder.files:
                    self.assertNotIn("\\", entry["path"],
                                     "paths are posix-relative")
                    self.assertNotIn("..", Path(entry["path"]).parts)
                    self.assertGreater(entry["size"], 0)
                    self.assertRegex(entry["sha256"], r"^[0-9A-F]{64}$")

    def test_excluded_files_are_not_also_pinned(self) -> None:
        for name, holder in sorted(self.corpus.sets.items()):
            with self.subTest(set=name):
                overlap = set(holder.excluded) & set(holder.relative_paths)
                self.assertFalse(overlap,
                                 "a file cannot be both evidence and excluded: %s"
                                 % sorted(overlap))

    def test_every_exclusion_carries_a_reason(self) -> None:
        for name, holder in sorted(self.corpus.sets.items()):
            for path, reason in sorted(holder.excluded.items()):
                with self.subTest(set=name, path=path):
                    self.assertGreater(
                        len(reason), 40,
                        "excluding %s must be justified in the table, not just "
                        "listed" % path)


class PinnedFilesTests(unittest.TestCase):
    """The files on disk match what is pinned."""

    def setUp(self) -> None:
        self.corpus = CaptureCorpus.load()

    def test_every_pinned_capture_is_present_and_byte_identical(self) -> None:
        for name in sorted(self.corpus.sets):
            with self.subTest(set=name):
                try:
                    resolved = self.corpus.resolve(name)
                except CaptureCorpusError as exc:
                    self.fail("%s\n%s" % (exc, FIX_HINT))
                self.assertEqual(len(resolved), len(self.corpus[name]))

    def test_no_capture_exists_outside_the_pinned_set(self) -> None:
        for name in sorted(self.corpus.sets):
            with self.subTest(set=name):
                strays = self.corpus[name].strays()
                self.assertFalse(
                    strays,
                    "unpinned capture(s) in set %r: %s\n%s"
                    % (name, strays, FIX_HINT))

    def test_no_pinned_capture_has_vanished(self) -> None:
        for name in sorted(self.corpus.sets):
            with self.subTest(set=name):
                self.assertFalse(self.corpus[name].vanished())

    def test_hashes_are_reproducible(self) -> None:
        # Spot-check the hashing itself against one small pinned file so a
        # broken sha256_of cannot make every comparison vacuously pass.
        holder = self.corpus["game_v141_archived"]
        entry = min(holder.files, key=lambda item: item["size"])
        path = ROOT / entry["path"]
        self.assertEqual(sha256_of(path), entry["sha256"])
        self.assertEqual(path.stat().st_size, entry["size"])


class LiveFileExclusionTests(unittest.TestCase):
    """The specific defect CORPUS-PIN-001 was opened for."""

    def setUp(self) -> None:
        self.holder = CaptureCorpus.load()["game_v141_archived"]

    def test_the_live_tails_are_excluded_by_name(self) -> None:
        self.assertEqual(set(self.holder.excluded), LIVE_FILES)

    def test_the_live_tails_still_match_the_pattern(self) -> None:
        # If they stopped matching, the exclusion would be dead weight and the
        # next reader would delete it.  They DO match GAME_*.txt - that is why
        # the old glob counted them.
        scanned = set(self.holder.scan())
        for live in LIVE_FILES:
            with self.subTest(path=live):
                if (ROOT / live).is_file():
                    self.assertIn(live, scanned)

    def test_the_pinned_denominator_excludes_them(self) -> None:
        for live in LIVE_FILES:
            self.assertNotIn(live, self.holder.relative_paths)


class StrayDetectionTests(unittest.TestCase):
    """Prove the trap fires, on a throwaway tree - never on the real corpus."""

    def _sandbox(self, tmp: str):
        root = Path(tmp)
        (root / "capture_fake").mkdir()
        good = root / "capture_fake" / "GAME_20260101_000000_000000_1.txt"
        good.write_bytes(b"pinned evidence\n")
        spec = {
            "description": "throwaway",
            "scan_dir": "capture_fake",
            "pattern": "GAME_*.txt",
            "recursive": False,
            "excluded": {},
            "files": [{
                "path": "capture_fake/GAME_20260101_000000_000000_1.txt",
                "size": good.stat().st_size,
                "sha256": sha256_of(good),
            }],
        }
        return root, spec

    def test_clean_tree_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, spec = self._sandbox(tmp)
            holder = CaptureSet("fake", spec, root)
            holder.resolve()
            holder.assert_no_strays()

    def test_one_unexpected_capture_is_enough_to_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, spec = self._sandbox(tmp)
            stray = root / "capture_fake" / "GAME_20260819_999999_999999_9.txt"
            stray.write_bytes(b"written by a job with no --capture-root\n")
            holder = CaptureSet("fake", spec, root)
            holder.resolve()  # the pinned file is still fine...
            with self.assertRaises(CaptureCorpusError) as caught:
                holder.assert_no_strays()  # ...but the set is not
            self.assertIn(stray.name, str(caught.exception))

    def test_a_rewritten_capture_is_content_drift_not_a_count_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, spec = self._sandbox(tmp)
            good = root / spec["files"][0]["path"]
            good.write_bytes(b"pinned evidence\n" + b"appended by a live run\n")
            holder = CaptureSet("fake", spec, root)
            holder.assert_no_strays()  # the count never moved
            with self.assertRaises(CaptureCorpusError) as caught:
                holder.resolve()
            self.assertIn("drift", str(caught.exception))

    def test_an_excluded_file_is_not_a_stray(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, spec = self._sandbox(tmp)
            spec = copy.deepcopy(spec)
            live = root / "capture_fake" / "GAME_LIVE.txt"
            live.write_bytes(b"rewritten every run\n")
            spec["excluded"] = {
                "capture_fake/GAME_LIVE.txt":
                    "live tail, rewritten on every run - not evidence, and "
                    "excluded here on purpose so the decision is recorded",
            }
            holder = CaptureSet("fake", spec, root)
            holder.assert_no_strays()
            self.assertNotIn("capture_fake/GAME_LIVE.txt", holder.relative_paths)

    def test_a_missing_pinned_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, spec = self._sandbox(tmp)
            (root / spec["files"][0]["path"]).unlink()
            holder = CaptureSet("fake", spec, root)
            with self.assertRaises(CaptureCorpusError):
                holder.resolve()
            self.assertEqual(holder.vanished(), [spec["files"][0]["path"]])


if __name__ == "__main__":
    unittest.main()
