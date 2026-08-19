"""Pin RUNTIMERES-ACTOR-ENTRY-001's answer to the bytes it was read from.

The chief's standing note - carried unchecked for three rounds - was:

    "the RuntimeRes actor-entry pipe is the only path that reaches _F_DIE_000"

That sentence is a claim about **counts of entry points**, and counts are
exactly the kind of claim that rots silently.  These tests re-run
``tools/pf_runtimeres_actor_entry_static.py`` against the real, hash-pinned
client image (never a mock, never a recorded output) and compare every number
in the report's ``RUNTIMERES_COUNTS`` block against that live run.

They also carry **trap tests**.  A verifier that cannot be made to fail is not
a verifier, it is a printout.  Each trap mutates one byte (or splices a few
bytes) into an in-memory COPY of the image, asserts that the specific guard
which is supposed to notice actually rejects, and then restores the image and
asserts the real bytes survived:

  1. flipping a byte inside a frozen function span breaks its span hash;
  2. neutering the single ``E8`` at 0x444705 changes the complete entry-point
     census of 0x4437C0 and makes ``gentry`` reject;
  3. planting the little-endian dword 0x004437C0 anywhere in the file makes the
     "zero pointer occurrences" half of that census reject - this is the trap
     that guards against a vtable-dispatched death path being missed;
  4. splicing a ``mov edx,[eax+0x20] ... call edx`` shape into the
     UpdateAttrVital handler makes the "it contains zero vtable+0x20
     dispatches" negative reject.

Trap 3 and trap 4 are the two that matter most: they are the exact failure
modes round 83 was exposed to (a linear disassembler that stops early, and a
negative asserted over a region nobody swept).

Re-pinning when a number legitimately moves (a different client build, a src/
edit that changes a call-site count): run
``py -3 tools/pf_runtimeres_actor_entry_static.py --json`` and update the
``RUNTIMERES_COUNTS`` block in the report in the same change.

These tests import nothing from ``src/``, open no socket, touch no database,
boot no server and launch no GameClient.  They need **no capstone** and no
third-party package at all - they read one binary and a handful of text files.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import re
import struct
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "pf_runtimeres_actor_entry_static.py"
REPORT = (
    ROOT / "reports"
    / "PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md"
)
CLIENT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

COUNTS_BLOCK = re.compile(r"```json RUNTIMERES_COUNTS\n(?P<body>.*?)\n```", re.S)

_TOOL_MODULE = None


def load_tool():
    """Execute the verifier once against the real image.

    A drifted guard raises SystemExit here, so the very first test fails loudly
    instead of every later assertion failing mysteriously.
    """
    global _TOOL_MODULE
    if _TOOL_MODULE is None:
        spec = importlib.util.spec_from_file_location(
            "pf_runtimeres_actor_entry_static", TOOL)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        with redirect_stdout(io.StringIO()):
            spec.loader.exec_module(module)
        _TOOL_MODULE = module
    return _TOOL_MODULE


def report_counts():
    text = REPORT.read_text(encoding="utf-8")
    m = COUNTS_BLOCK.search(text)
    assert m, "the report must carry a ```json RUNTIMERES_COUNTS block"
    return json.loads(m.group("body"))


@contextlib.contextmanager
def patched(tool, patches):
    """Swap in a mutated copy of the image, quarantine the guard bookkeeping,
    then restore everything.  `patches` is [(file_offset, bytes), ...]."""
    original = tool.data
    fails_before, nguard_before = list(tool.FAILS), tool.NGUARD
    buf = bytearray(original)
    for off, blob in patches:
        buf[off:off + len(blob)] = blob
    tool.data = bytes(buf)
    try:
        yield
    finally:
        tool.data = original
        tool.FAILS[:] = fails_before
        tool.NGUARD = nguard_before


@contextlib.contextmanager
def flipped(tool, va, mask=0x01):
    off = tool.va2off(va)
    assert off is not None, "0x%08X is not mapped" % va
    with patched(tool, [(off, bytes([tool.data[off] ^ mask]))]):
        yield


class TestVerifierItself(unittest.TestCase):
    def test_the_verifier_runs_clean_against_the_pinned_image(self):
        tool = load_tool()
        self.assertEqual(tool.FAILS, [], "a static guard drifted")
        self.assertGreaterEqual(tool.NGUARD, 140)
        self.assertEqual(tool.SHA, CLIENT_SHA)
        self.assertEqual(
            hashlib.sha256(Path(tool.BIN).read_bytes()).hexdigest().upper(),
            CLIENT_SHA)

    def test_it_needs_no_third_party_package(self):
        src = TOOL.read_text(encoding="utf-8")
        for banned in ("capstone", "pefile", "import numpy", "import yaml"):
            self.assertNotIn(banned + "\n", src)
        self.assertNotIn("import capstone", src)

    def test_it_sweeps_both_executable_sections(self):
        """Round 83's sweep only knew about .text.  This image has two."""
        tool = load_tool()
        self.assertEqual([s[0] for s in tool.EXEC_SECS], [".text", ".code"])


class TestReportMatchesTheBinary(unittest.TestCase):
    def test_every_number_in_the_report_comes_from_the_tool(self):
        tool = load_tool()
        want = report_counts()
        got = tool.COUNTS
        self.assertEqual(set(want), set(got),
                         "the report's COUNTS keys drifted from the tool's")
        for key in sorted(want):
            self.assertEqual(want[key], got[key],
                             "report key %r disagrees with the binary" % key)

    def test_the_report_states_the_guard_count_it_actually_has(self):
        self.assertEqual(report_counts()["guards"], load_tool().NGUARD)


class TestTheAnswer(unittest.TestCase):
    """Restate the load-bearing conclusions independently of the report prose,
    so a silent edit to either file cannot quietly change them."""

    def test_the_string_RuntimeRes_is_not_in_the_image_at_all(self):
        tool = load_tool()
        for missing in ("RuntimeRes", "RunTimeRes", "RuntimeProtocol"):
            self.assertEqual(tool.data.find(missing.encode("latin1")), -1,
                             "%r unexpectedly present" % missing)
        self.assertEqual(tool.cstr(0xF2FFF8), "GSCN_RunTimeProtocolRes")

    def test_the_res_id_matches_the_number_the_client_reported_live(self):
        tool = load_tool()
        self.assertEqual(tool.name_id("GSCN_RunTimeProtocolRes"), 0x6E9D)
        self.assertEqual(0x6E9D, 28317)
        self.assertEqual(tool.name_id("GSCN_RunTimeProtocolReq"), 0x6E6F)

    def test_the_three_round83_targets_have_the_entry_counts_claimed(self):
        tool = load_tool()
        self.assertEqual(tool.entry_points(0x4437C0),
                         {"direct_calls": [0x444705], "tail_jumps": [],
                          "pointer_slots": []})
        self.assertEqual(tool.entry_points(0x472810),
                         {"direct_calls": [0x4439E9], "tail_jumps": [],
                          "pointer_slots": []})
        self.assertEqual(tool.entry_points(0x472850),
                         {"direct_calls": [], "tail_jumps": [],
                          "pointer_slots": [0xF0F054]})

    def test_the_actor_entry_dispatcher_has_exactly_one_caller(self):
        tool = load_tool()
        self.assertEqual(tool.entry_points(0x446F30),
                         {"direct_calls": [0x5E4085], "tail_jumps": [],
                          "pointer_slots": []})
        # and that one caller is inside the GSCN_RunTimeProtocolRes handler
        self.assertTrue(0x5E4060 <= 0x5E4085 < 0x5E41CD)
        self.assertEqual(tool.dw(0xF2FFC0 + 0x1C), 0x5E4060)

    def test_updateattrvital_cannot_reach_the_death_chain(self):
        tool = load_tool()
        self.assertEqual(tool.vt20_dispatch_sites(0x5F2400, 0x5F261A), [])
        for target in (0x4446F0, 0x456630, 0x4437C0, 0x446F30):
            self.assertFalse(
                any(0x5F2400 <= c < 0x5F261A for c in tool.calls_to(target)))

    def test_the_two_predicates_have_opposite_timer_polarity(self):
        tool = load_tool()
        # +0x40 uses `movss xmm0,[attr+0x58] ; comiss xmm0,[0xF0989C]`
        self.assertIn(bytes.fromhex("f30f1040580f2f059c98f000"),
                      tool.span(0x43BDA0, 0x43BDD3))
        # +0x3C uses `xorps xmm0,xmm0 ; comiss xmm0,[attr+0x58]` - reversed
        self.assertIn(bytes.fromhex("0f57c00f2f4058"),
                      tool.span(0x43BD70, 0x43BD9E))
        self.assertEqual(struct.unpack("<f", tool.rd(0xF0989C, 4))[0], 0.0)

    def test_a_first_sight_actor_takes_the_spawn_path_and_cannot_dead_sync(self):
        tool = load_tool()
        # the spawn apply goes through vtable +0x10 ...
        self.assertIn(bytes.fromhex("8b068b5010558bceffd2"),
                      tool.span(0x446990, 0x446B2C))
        # ... and 0x4437C0 still has exactly one caller, which is not it
        self.assertEqual(tool.calls_to(0x4437C0), [0x444705])

    def test_the_actor_type_gate_is_2_through_6(self):
        tool = load_tool()
        self.assertIn(bytes.fromhex("0fb6401083c0fe"), tool.span(0x4469C0, 0x4469E0))
        self.assertEqual([tool.dw(0x446B2C + i * 4) for i in range(5)],
                         [0x4469E1, 0x4469F7, 0x446A3D, 0x446A5A, 0x446A77])

    def test_the_server_gap_was_three_specific_zeros_and_round_86_closed_them(self):
        """Round 85 wrote three zeros here and called them the server-side gap.

        Round 86 built RUNTIMERES-ENCODER-001 to close them, so this test is
        re-pinned to the closure rather than deleted: it now fails if somebody
        removes the emitter, which is the direction that would actually cost
        us something.  See ERRATUM 1 in the report.
        """
        counts = load_tool().COUNTS
        # gap 1 and gap 3: exactly one module now does both, and it is named,
        # so adding a second emitter is a red line that says whose file it is
        # rather than an arithmetic disagreement about a bare count.
        self.assertEqual(counts["src_modules_doing_both"], 1)
        self.assertEqual(counts["src_modules_doing_both_names"],
                         ["runtimeres_death_hypothesis.py"])
        self.assertEqual(counts["actionable_server_gaps"], 0)
        self.assertEqual(counts["src_actor_stream_call_sites"], 5)
        # gap 2 is the one worth keeping a test on.  The round-85 measure -
        # the literal `current_hp = 0` - is STILL zero, because the encoder
        # passes its zero through a named constant.  That guard was about to
        # stay green while its sentence stopped being true, so both halves are
        # asserted here: the old measure and the one that actually notices.
        self.assertEqual(counts["server_call_sites_emitting_zero_current_hp"], 0)
        self.assertEqual(counts["src_modules_passing_zero_hp_by_named_constant"],
                         ["runtimeres_death_hypothesis.py"])

    def test_the_erratum_is_present_and_does_not_rewrite_the_original(self):
        """The published prose keeps its wrong sentence; the erratum follows it.

        Same shape as tests/test_hp_death_erratum.py: making the record tidy by
        making it false has to be as red as not correcting it at all.
        """
        text = REPORT.read_text(encoding="utf-8")
        original = 'Each is a countable zero today.'
        erratum = "## ERRATUM 1 --- round 86"
        erratum = erratum.replace("---", "—")
        self.assertIn(original, text,
                      "the original sentence must survive verbatim")
        self.assertIn(erratum, text, "the erratum must be present")
        self.assertLess(text.index(original), text.index(erratum),
                        "the erratum must come after the claim it corrects")


class TestTraps(unittest.TestCase):
    """A verifier that cannot be made to fail is not a verifier."""

    def test_trap1_flipping_a_byte_in_a_frozen_span_breaks_its_hash(self):
        tool = load_tool()
        lo, hi = 0x4437C0, 0x443A9A
        sha = "85d294b84843e0bd46256e0257cf5d51be0415081739d82b0b4c254975ee9592"
        self.assertEqual(tool.span_sha(lo, hi), sha)
        with flipped(tool, lo + (hi - lo) // 2):
            self.assertNotEqual(tool.span_sha(lo, hi), sha)
            self.assertFalse(tool.gspan(lo, hi, sha, "trap"))
        self.assertEqual(tool.span_sha(lo, hi), sha)
        self.assertEqual(tool.FAILS, [])

    def test_trap2_neutering_the_only_call_site_breaks_the_census(self):
        """0x444705 is the ONE thing that makes 0x4437C0 reachable.  Turn its
        E8 into a NOP and the complete-census guard must reject."""
        tool = load_tool()
        off = tool.va2off(0x444705)
        self.assertEqual(tool.data[off], 0xE8)
        with patched(tool, [(off, b"\x90")]):
            self.assertEqual(tool.calls_to(0x4437C0), [])
            self.assertFalse(
                tool.gentry(0x4437C0, [0x444705], [], "trap"))
        self.assertEqual(tool.calls_to(0x4437C0), [0x444705])
        self.assertEqual(tool.FAILS, [])

    def test_trap3_a_planted_vtable_pointer_is_caught(self):
        """THE trap that matters: a function reached only through a table has
        no E8 anywhere.  Plant the dword 0x004437C0 in .rdata and the
        pointer half of the census must reject."""
        tool = load_tool()
        self.assertEqual(tool.dword_vas(0x4437C0), [])
        slot_va = 0xC3BC00                 # a zero-filled, unreferenced .rdata dword
        off = tool.va2off(slot_va)
        self.assertEqual(tool.rd(slot_va, 4), b"\0\0\0\0")
        with patched(tool, [(off, struct.pack("<I", 0x4437C0))]):
            self.assertEqual(tool.dword_vas(0x4437C0), [slot_va])
            self.assertFalse(
                tool.gentry(0x4437C0, [0x444705], [], "trap"))
        self.assertEqual(tool.dword_vas(0x4437C0), [])
        self.assertEqual(tool.FAILS, [])

    def test_trap4_a_spliced_vt20_dispatch_breaks_the_negative(self):
        """The UpdateAttrVital negative is asserted over a whole span.  Splice
        the dispatch shape into that span and it must reject."""
        tool = load_tool()
        self.assertEqual(tool.vt20_dispatch_sites(0x5F2400, 0x5F261A), [])
        target_va = 0x5F2500
        off = tool.va2off(target_va)
        # `mov eax,[edx] ; mov edx,[eax+0x20] ; call edx`
        shape = bytes.fromhex("8b028b5020ffd2")
        with patched(tool, [(off, shape)]):
            hits = tool.vt20_dispatch_sites(0x5F2400, 0x5F261A)
            self.assertEqual(hits, [target_va + 2])
            self.assertFalse(tool.guard(hits == [], "trap"))
        self.assertEqual(tool.vt20_dispatch_sites(0x5F2400, 0x5F261A), [])
        self.assertEqual(tool.FAILS, [])

    def test_trap5_corrupting_the_die_literal_is_caught(self):
        tool = load_tool()
        self.assertEqual(tool.wstr(0xF0F060), "_F_DIE_000")
        with flipped(tool, 0xF0F060 + 2):
            self.assertNotEqual(tool.wstr(0xF0F060), "_F_DIE_000")
            self.assertFalse(tool.gbytes(
                0xF0F060, "5f0046005f004400490045005f00300030003000", "trap"))
        self.assertEqual(tool.wstr(0xF0F060), "_F_DIE_000")
        self.assertEqual(tool.FAILS, [])

    def test_the_real_binary_survived_every_trap(self):
        tool = load_tool()
        self.assertEqual(hashlib.sha256(tool.data).hexdigest().upper(),
                         CLIENT_SHA)
        self.assertEqual(
            hashlib.sha256(Path(tool.BIN).read_bytes()).hexdigest().upper(),
            CLIENT_SHA)
        self.assertEqual(tool.FAILS, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
