"""LANE-B: the sha256 digest helper in ``tools/pf_mine_scene_mob_roster.py``
had no test of its own that runs with no bridge clone present.

WHY THIS FILE EXISTS.  Round `hor2lh` (reserve item 3) named the gap without
paying it: ``_digest`` (``tools/pf_mine_scene_mob_roster.py``) is what stamps
``SOURCE_DIGESTS`` into every generated ``field_mob_tables_bg####.py`` module,
and the only tests that exercise it end to end are the
``test_regenerating_reproduces_the_committed_module_byte_for_byte`` cases in
each scene's own test file -- every one of them decorated with
``@BRIDGE_GAMEDATA.skip_unless_present()``.  MEASURED this round: replacing
``_digest`` with a constant string (``"deadbeef" * 8``) left the full suite
green in a worktree with no ``pf_bridge`` beside it (15 skipped, 0 failed) --
the exact shape the Windows gate runs in, per ``NOW.md``'s own note that the
gate has no bridge next to it.  This file drives ``_digest`` directly, so
that gap runs everywhere, bridge or no bridge.

WHAT THIS DOES NOT CLAIM.  It says nothing about whether any scene's shipped
``SOURCE_DIGESTS`` are still fresh against the live bridge tables -- that is
what the (bridge-gated) regenerate-and-diff tests are for, and this file does
not replace them.  It only says the digest FUNCTION computes real sha256 of
the bytes it is given, using inputs this file owns rather than the bridge's.
"""
from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "pf_mine_scene_mob_roster", TOOL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DigestGuardTests(unittest.TestCase):
    """No bridge clone required -- must run wherever the gate runs."""

    def test_digest_of_the_empty_file_is_the_published_sha256_constant(
            self) -> None:
        # sha256("") is a widely published, independently-checkable constant.
        # A mutant that returns anything hash-shaped but not real sha256
        # cannot agree with this literal by accident.
        tool = _load_tool()
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "empty.tsv"
            path.write_bytes(b"")
            self.assertEqual(
                tool._digest(path),
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991"
                "b7852b855",
            )

    def test_digest_of_a_known_vector_matches_the_published_sha256_of_abc(
            self) -> None:
        # A second, non-empty published NIST test vector, independent of the
        # first: a mutant that special-cased "empty file" could not also
        # agree here by accident.
        tool = _load_tool()
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "abc.tsv"
            path.write_bytes(b"abc")
            self.assertEqual(
                tool._digest(path),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff6"
                "1f20015ad",
            )

    def test_digest_reads_this_lanes_own_bytes_not_a_constant(self) -> None:
        # Two different files this test writes itself (not shipped game
        # data) must produce two different digests, and each must equal an
        # independently computed hashlib.sha256 of the exact bytes on disk
        # -- catches "_digest always returns the same string" directly,
        # without depending on any committed table.
        tool = _load_tool()
        with tempfile.TemporaryDirectory() as work:
            work = Path(work)
            first = work / "first.tsv"
            second = work / "second.tsv"
            first.write_bytes(b"n_ID\tn_RANK\n1\t2\n")
            second.write_bytes(b"n_ID\tn_RANK\n3\t4\n")
            digest_first = tool._digest(first)
            digest_second = tool._digest(second)
            self.assertNotEqual(digest_first, digest_second)
            self.assertEqual(
                digest_first, hashlib.sha256(first.read_bytes()).hexdigest())
            self.assertEqual(
                digest_second,
                hashlib.sha256(second.read_bytes()).hexdigest())

    def test_digest_is_lowercase_hex_of_the_right_length(self) -> None:
        # SOURCE_DIGESTS is read as a fixed-width field by every generated
        # module's docstring table; a digest of the wrong shape would still
        # "work" until someone diffed the printed table by eye.
        tool = _load_tool()
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "sample.tsv"
            path.write_bytes(b"anything\n")
            digest = tool._digest(path)
            self.assertEqual(len(digest), 64)
            self.assertEqual(digest, digest.lower())
            self.assertTrue(all(c in "0123456789abcdef" for c in digest))


if __name__ == "__main__":
    unittest.main()
