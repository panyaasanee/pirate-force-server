"""SCAN-DEBT-001 - ``tools/pf_teleportcheck_0x4477_static.py`` must be able to fail.

Before round 84 that verifier globbed for its wire corpus in the game install
tree one level above the repository, found nothing when run from the repository
root, printed ``SKIP wire corpus (capture files not reachable from this path)``
and **exited 0**.  It had been reporting success without reading a single byte
of wire evidence for two rounds.

The fix reads the corpus out of ``docs/PF_CAPTURE_CORPUS.json`` (set
``game_teleportcheck_0x4477``) and fails closed.  These tests exist to prove
that the new guards actually fire, because "it passes on the real corpus" is
exactly the observation the old version also satisfied.

Every trap builds a throwaway tree under ``tmp_path``.  Nothing here writes into
``evidence/``, ``capture_v141/``, ``references/``, ``state/`` or ``backups/``,
opens a socket, touches a database or launches the client.  Pure stdlib - this
file deliberately imports neither ``pefile`` nor ``capstone`` so that it runs in
every environment the gate runs in.

Run just this file:
    python3 -m pytest tests/test_teleportcheck_0x4477_corpus.py -q
"""
from __future__ import annotations

import ast
import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.pf_capture_corpus import DEFAULT_TABLE, CaptureCorpus, CaptureCorpusError
from tools.pf_teleportcheck_0x4477_static import (
    CORPUS_SET,
    EXPECTED_INBOUND_COUNT,
    EXPECTED_INBOUND_FRAME,
    UNPINNABLE_SESSIONS,
    Guards,
    inbound_0x4477,
    inbound_frames,
    main,
    wire_guards,
)

TOOL = Path(__file__).resolve().parents[1] / "tools" / "pf_teleportcheck_0x4477_static.py"

# A capture journal in miniature: one inbound frame carrying 0x4477, and one
# outbound composition carrying the same bytes.  A direction-blind substring
# search sees two; the decoder must see one.
SYNTHETIC_CAPTURE = """\
FRAME magic=0x5F253EAC compressed_len=25
00000000  AC 3E 25 5F 19 00 00 00 17 58 12 6F 6E 14 00 00
00000010  00 00 08 00 0B 02 12 01 00 12 77 44 0B 00 0F 01
00000020  00
DECOMPRESSED 23
00000000  12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12
00000010  77 44 0B 00 0F 01 00
STRUCTURAL_IDS [(0, 28271, 'GSCN_RunTimeProtocolReq'), (15, 17527, 'TeleportCheckVital')] OUTER version=0 mask=0x02 count=1 nested_version=0
STATE rx=64 teleportcheck_reply=0
SENT V136_COMPOSITIONAL_MARKER1_DOCKING_PROMPT_ONCE bytes=35
PC 25
00000000  12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12
00000010  77 44 0B 00 0F 01 00 0B 00
FRAME
00000000  AC 3E 25 5F 1B 00 00 00 19 60 12 9D 6E 14 00 00
00000010  00 00 08 04 0B 02 12 01 00 12 77 44 0B 00 0F 01
00000020  00 0B 00
"""


def _sandbox(root: Path, body: str = SYNTHETIC_CAPTURE) -> dict:
    """A one-file corpus set on a throwaway tree, shaped like the real one."""
    from tools.pf_capture_corpus import sha256_of

    directory = root / "backups" / "vFAKE_20260101_000000" / "capture_vFAKE"
    directory.mkdir(parents=True)
    capture = directory / "GAME_20260101_000000_000000_1.txt"
    capture.write_text(body, encoding="utf-8")
    rel = capture.relative_to(root).as_posix()
    return {
        "sets": {
            CORPUS_SET: {
                "description": "throwaway",
                "scan_dirs": [directory.relative_to(root).as_posix()],
                "pattern": "GAME_2*.txt",
                "recursive": False,
                "excluded": {},
                "files": [{
                    "path": rel,
                    "size": capture.stat().st_size,
                    "sha256": sha256_of(capture),
                }],
                "file_count": 1,
            }
        }
    }


def _run_wire(root: Path, data: dict, expected: dict) -> Guards:
    """Run only the wire guards against a sandbox corpus."""
    import tools.pf_teleportcheck_0x4477_static as tool

    guards = Guards()
    original = tool.EXPECTED_INBOUND_COUNT
    try:
        tool.EXPECTED_INBOUND_COUNT = expected
        tool.wire_guards(guards, corpus=CaptureCorpus(data, root))
    finally:
        tool.EXPECTED_INBOUND_COUNT = original
    return guards


class FrameDecodingTests(unittest.TestCase):
    """Direction matters: an outbound composition is not wire evidence."""

    def test_only_the_inbound_frame_is_decoded(self):
        frames = list(inbound_frames(SYNTHETIC_CAPTURE))
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0][1], EXPECTED_INBOUND_FRAME)

    def test_a_substring_count_would_have_got_this_wrong(self):
        # The exact defect the old check had.  The byte string appears four
        # times in this fixture - inbound compressed, inbound decompressed,
        # outbound composed, outbound framed - and exactly ONE of those is a
        # client->server frame.  If this ever stops being true the fixture has
        # drifted and the decoder test above it means nothing.
        self.assertEqual(SYNTHETIC_CAPTURE.count("77 44 0B 00 0F 01"), 4)
        self.assertEqual(len(inbound_0x4477(SYNTHETIC_CAPTURE)), 1)

    def test_a_frame_without_structural_ids_is_not_counted(self):
        # DECOMPRESSED with no resolver line following it = nothing was decoded,
        # so nothing may be claimed.
        text = SYNTHETIC_CAPTURE.replace("STRUCTURAL_IDS ", "STATE_IDS ")
        self.assertEqual(list(inbound_frames(text)), [])


class RealCorpusTests(unittest.TestCase):
    """The pinned set is intact and the tool reproduces it."""

    def test_the_set_is_declared_in_the_tracked_table(self):
        raw = json.loads(DEFAULT_TABLE.read_text(encoding="utf-8"))
        self.assertIn(CORPUS_SET, raw["sets"])
        spec = raw["sets"][CORPUS_SET]
        self.assertIn("scan_dirs", spec)
        self.assertEqual(spec["pattern"], "GAME_2*.txt")
        self.assertEqual(spec["file_count"], len(EXPECTED_INBOUND_COUNT))

    def test_the_wire_guards_all_pass_on_the_real_corpus(self):
        guards = Guards()
        wire_guards(guards)
        self.assertEqual(guards.failures, [])

    def test_the_numerator_and_denominator_are_both_pinned_by_name(self):
        positives = [k for k, v in EXPECTED_INBOUND_COUNT.items() if v == 1]
        negatives = [k for k, v in EXPECTED_INBOUND_COUNT.items() if v == 0]
        self.assertEqual(len(positives), 6)
        self.assertEqual(len(negatives), 1)
        self.assertEqual(len(UNPINNABLE_SESSIONS), 2)

    def test_the_tool_never_prints_skip_again(self):
        # The literal regression: a verifier that answers "not reachable from
        # this path" by printing SKIP and returning success.  Prose about SKIP
        # is fine (this file is full of it); a print statement is not.
        # Parsed, not grepped: the module docstring quotes the old code on
        # purpose, and a text search cannot tell a quotation from a statement.
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

    def test_the_tool_needs_no_third_party_disassembler(self):
        # It imported capstone, built one Cs object and never used it, which is
        # why it could not run in the gate environment at all.
        source = TOOL.read_text(encoding="utf-8")
        for banned in ("import capstone", "from capstone", "import pefile"):
            self.assertNotIn(banned, source)


class TrapTests(unittest.TestCase):
    """A guard that cannot fail is not a guard."""

    def test_a_vanished_capture_raises_instead_of_skipping(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _sandbox(root)
            (root / data["sets"][CORPUS_SET]["files"][0]["path"]).unlink()
            with self.assertRaises(CaptureCorpusError) as caught:
                _run_wire(root, data, {})
            self.assertIn("missing", str(caught.exception))

    def test_a_rewritten_capture_raises_content_drift(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _sandbox(root)
            target = root / data["sets"][CORPUS_SET]["files"][0]["path"]
            target.write_text(SYNTHETIC_CAPTURE + "APPENDED BY A LIVE RUN\n",
                              encoding="utf-8")
            with self.assertRaises(CaptureCorpusError) as caught:
                _run_wire(root, data, {})
            self.assertIn("drift", str(caught.exception))

    def test_an_extra_capture_in_the_folder_raises(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _sandbox(root)
            stray = (root / data["sets"][CORPUS_SET]["files"][0]["path"]).parent
            (stray / "GAME_20260819_999999_999999_9.txt").write_text(
                "written by a job with no --capture-root\n", encoding="utf-8")
            with self.assertRaises(CaptureCorpusError) as caught:
                _run_wire(root, data, {})
            self.assertIn("not", str(caught.exception))

    def test_a_capture_whose_frame_changed_fails_even_though_it_is_pinned(self):
        """count != content, the other way round: hash agrees, bytes do not."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            mutated = SYNTHETIC_CAPTURE.replace("0F 01 00\n", "0F 02 00\n")
            self.assertNotEqual(mutated, SYNTHETIC_CAPTURE)
            data = _sandbox(root, body=mutated)  # pinned to the MUTATED bytes
            rel = data["sets"][CORPUS_SET]["files"][0]["path"]
            guards = _run_wire(root, data, {rel: 1})
            self.assertTrue(
                [name for name in guards.failures if "pinned 23-byte record" in name],
                guards.rows)

    def test_a_wrong_inbound_count_fails(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _sandbox(root)
            rel = data["sets"][CORPUS_SET]["files"][0]["path"]
            guards = _run_wire(root, data, {rel: 99})
            self.assertTrue(
                [name for name in guards.failures if "inbound 0x4477 frame" in name],
                guards.rows)

    def test_a_pinned_file_missing_from_the_expectation_table_fails(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _sandbox(root)
            guards = _run_wire(root, data, {"some/other/path.txt": 1})
            self.assertTrue(guards.failures, guards.rows)

    def test_an_empty_scan_dirs_list_is_refused(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _sandbox(root)
            broken = copy.deepcopy(data)
            broken["sets"][CORPUS_SET]["scan_dirs"] = []
            with self.assertRaises(CaptureCorpusError):
                CaptureCorpus(broken, root)

    def test_declaring_both_scan_dir_and_scan_dirs_is_refused(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _sandbox(root)
            broken = copy.deepcopy(data)
            broken["sets"][CORPUS_SET]["scan_dir"] = "."
            with self.assertRaises(CaptureCorpusError):
                CaptureCorpus(broken, root)


class ExitCodeTests(unittest.TestCase):
    """The end-to-end behaviour, which is the thing that was actually broken."""

    def test_an_unreachable_client_image_is_a_nonzero_exit(self):
        with TemporaryDirectory() as tmp:
            missing = Path(tmp) / "there-is-no-GameClient.local.bin"
            self.assertNotEqual(main([str(missing)]), 0)

    def test_an_unreachable_corpus_is_a_nonzero_exit(self):
        import tools.pf_teleportcheck_0x4477_static as tool

        with TemporaryDirectory() as tmp:
            original = tool.CaptureCorpus.load

            def _explode(*args, **kwargs):
                raise CaptureCorpusError("capture corpus table not found (synthetic)")

            tool.CaptureCorpus.load = staticmethod(_explode)
            try:
                self.assertNotEqual(main(["--skip-binary"]), 0)
            finally:
                tool.CaptureCorpus.load = original

    def test_the_real_run_still_passes(self):
        self.assertEqual(main([]), 0)


if __name__ == "__main__":
    unittest.main()
