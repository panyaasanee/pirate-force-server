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
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

# load_tool() makes the verifier read ../GameClient/GameClient.local.bin, a
# proprietary binary that can never be in a fresh clone, so every test that
# calls it must say so and skip without it.  See tests/pf_preconditions.py.
from pf_preconditions import CLIENT_IMAGE  # noqa: E402

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
    # Method-level guards, not a class one: the source-only check below runs
    # fine without the client image.  See tests/pf_preconditions.py.
    @CLIENT_IMAGE.skip_unless_present()
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

    @CLIENT_IMAGE.skip_unless_present()
    def test_it_sweeps_both_executable_sections(self):
        """Round 83's sweep only knew about .text.  This image has two."""
        tool = load_tool()
        self.assertEqual([s[0] for s in tool.EXEC_SECS], [".text", ".code"])


# Every test compares the report against a live run over the client image,
# which a fresh clone never has.  See tests/pf_preconditions.py.
@CLIENT_IMAGE.skip_unless_present()
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

    # Method-level guards, not a class one: the erratum test below reads only
    # the report and must keep running.  See tests/pf_preconditions.py.
    @CLIENT_IMAGE.skip_unless_present()
    def test_the_string_RuntimeRes_is_not_in_the_image_at_all(self):
        tool = load_tool()
        for missing in ("RuntimeRes", "RunTimeRes", "RuntimeProtocol"):
            self.assertEqual(tool.data.find(missing.encode("latin1")), -1,
                             "%r unexpectedly present" % missing)
        self.assertEqual(tool.cstr(0xF2FFF8), "GSCN_RunTimeProtocolRes")

    @CLIENT_IMAGE.skip_unless_present()
    def test_the_res_id_matches_the_number_the_client_reported_live(self):
        tool = load_tool()
        self.assertEqual(tool.name_id("GSCN_RunTimeProtocolRes"), 0x6E9D)
        self.assertEqual(0x6E9D, 28317)
        self.assertEqual(tool.name_id("GSCN_RunTimeProtocolReq"), 0x6E6F)

    @CLIENT_IMAGE.skip_unless_present()
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

    @CLIENT_IMAGE.skip_unless_present()
    def test_the_actor_entry_dispatcher_has_exactly_one_caller(self):
        tool = load_tool()
        self.assertEqual(tool.entry_points(0x446F30),
                         {"direct_calls": [0x5E4085], "tail_jumps": [],
                          "pointer_slots": []})
        # and that one caller is inside the GSCN_RunTimeProtocolRes handler
        self.assertTrue(0x5E4060 <= 0x5E4085 < 0x5E41CD)
        self.assertEqual(tool.dw(0xF2FFC0 + 0x1C), 0x5E4060)

    @CLIENT_IMAGE.skip_unless_present()
    def test_updateattrvital_cannot_reach_the_death_chain(self):
        tool = load_tool()
        self.assertEqual(tool.vt20_dispatch_sites(0x5F2400, 0x5F261A), [])
        for target in (0x4446F0, 0x456630, 0x4437C0, 0x446F30):
            self.assertFalse(
                any(0x5F2400 <= c < 0x5F261A for c in tool.calls_to(target)))

    @CLIENT_IMAGE.skip_unless_present()
    def test_the_two_predicates_have_opposite_timer_polarity(self):
        tool = load_tool()
        # +0x40 uses `movss xmm0,[attr+0x58] ; comiss xmm0,[0xF0989C]`
        self.assertIn(bytes.fromhex("f30f1040580f2f059c98f000"),
                      tool.span(0x43BDA0, 0x43BDD3))
        # +0x3C uses `xorps xmm0,xmm0 ; comiss xmm0,[attr+0x58]` - reversed
        self.assertIn(bytes.fromhex("0f57c00f2f4058"),
                      tool.span(0x43BD70, 0x43BD9E))
        self.assertEqual(struct.unpack("<f", tool.rd(0xF0989C, 4))[0], 0.0)

    @CLIENT_IMAGE.skip_unless_present()
    def test_a_first_sight_actor_takes_the_spawn_path_and_cannot_dead_sync(self):
        tool = load_tool()
        # the spawn apply goes through vtable +0x10 ...
        self.assertIn(bytes.fromhex("8b068b5010558bceffd2"),
                      tool.span(0x446990, 0x446B2C))
        # ... and 0x4437C0 still has exactly one caller, which is not it
        self.assertEqual(tool.calls_to(0x4437C0), [0x444705])

    @CLIENT_IMAGE.skip_unless_present()
    def test_the_actor_type_gate_is_2_through_6(self):
        tool = load_tool()
        self.assertIn(bytes.fromhex("0fb6401083c0fe"), tool.span(0x4469C0, 0x4469E0))
        self.assertEqual([tool.dw(0x446B2C + i * 4) for i in range(5)],
                         [0x4469E1, 0x4469F7, 0x446A3D, 0x446A5A, 0x446A77])

    @CLIENT_IMAGE.skip_unless_present()
    def test_the_server_gap_was_three_specific_zeros_and_round_86_closed_them(self):
        """Round 85 wrote three zeros here and called them the server-side gap.

        Round 86 built RUNTIMERES-ENCODER-001 to close them, so this test is
        re-pinned to the closure rather than deleted: it now fails if somebody
        removes the emitter, which is the direction that would actually cost
        us something.  See ERRATUM 1 in the report.
        """
        counts = load_tool().COUNTS
        # gap 1 and gap 3: the modules that do both are named, so a new
        # emitter is a red line that says whose file it is rather than an
        # arithmetic disagreement about a bare count.
        # Round 111, HYP-PF-029 / NPC-HP-LINK-001, 1 -> 2.  This is the red
        # line doing its job: npc_hp_link_hypothesis.py is the second module
        # to both build an actor entry and SET bit 0x0080.  It is the first
        # lane in this tree that moves a TARGET's hit points, walking the
        # frozen NPC 0x2001 down 100, 100, 37, 37, 37, 37, 0, 0, and it exists
        # because an attended test on 2026-08-20 delivered 505 points of
        # damage as CHitResult frames and moved the target's HP bar by exactly
        # zero -- the client renders, it does not subtract, so the server has
        # to say both halves itself.  The count is re-pinned upward WITH both
        # names, never widened.
        # Round 170: 2 -> 3, and the third member needs its own sentence
        # because it is NOT a timer emitter.  HYP-PF-038
        # (hostile_hp_link_hypothesis.py) builds an actor entry and binds
        # BASIC_BIT_DEATH_TIMER = 0x0080, but its composer has no path that
        # ORs the bit into an emitted mask at all: _compose_npc_attr RAISES
        # when handed a timer and its basic_mask literal omits 0x0080.  The
        # module names the bit only so its own guards can refuse it -- which
        # is what remote_player_hypothesis.py does too, except that one binds
        # the value to a FORBIDDEN-named constant and so lands in the FORBID
        # census.  The discriminator keys on that constant name, so this lane
        # lands here instead.  The count is re-pinned upward rather than the
        # discriminator being narrowed, because narrowing it is how a real
        # emitter goes quiet: this census must be wrong in the direction that
        # over-reports.  A reader who needs "emits a timer today" must read
        # the composer, not this number.  The clean repair, when someone owns
        # that module, is to rename the constant with a FORBIDDEN marker.
        # Round swlc56: 3 -> 4.  mob_death.py (lane B, M4 second half) is the
        # fourth module that both builds an actor entry and SETS bit 0x0080 --
        # it is a production death lane, not a probe, so this census moving is
        # the lane working.  The tool's own guard was already re-pinned to 4
        # and to these four names; this file still said 3, and nothing noticed
        # because the whole module is excluded from the gate's client-free
        # subset and only runs on the bridge.
        self.assertEqual(counts["src_modules_doing_both"], 4)
        self.assertEqual(counts["src_modules_doing_both_names"],
                         ["hostile_hp_link_hypothesis.py",
                          "mob_death.py",
                          "npc_hp_link_hypothesis.py",
                          "runtimeres_death_hypothesis.py"])
        # Round 96: a second module (remote_player_hypothesis.py) now builds
        # actor entries and MENTIONS bit 0x0080, but only to FORBID it, so the
        # forbid census names the visibility probe.  This is the guard that
        # would catch a future actor_type 2 lane quietly emitting the death
        # timer.
        # Round 111: this count does NOT move, and that took a repair.  The
        # round-96 discriminator asked whether the whole module text contained
        # the substring "FORBIDDEN", and npc_hp_link_hypothesis.py carries an
        # unrelated FLAGS_FORBIDDEN_MASK = 0xF184, so a lane that genuinely
        # sets the death timer was filed under FORBID -- a measurement
        # artefact that held the SET census green at 1 while its sentence had
        # already stopped being true.  The tool now tests the bit itself
        # (DEATH_TIMER_FORBIDDEN_CONST), so FORBID means what it says.
        self.assertEqual(counts["src_modules_forbidding_basicattr_bit_0x0080"],
                         1)
        self.assertEqual(counts["src_modules_forbidding_names"],
                         ["remote_player_hypothesis.py"])
        self.assertEqual(counts["actionable_server_gaps"], 0)
        # Round 96: the two src/ actor-entry counts moved 5 -> 6 when the
        # remote-player probe was added; the death-chain claims above did not.
        # Round 99: they move 6 -> 7 for NPC-HOSTILE-001 (HYP-PF-027), which
        # spawns the same frozen NPC 0x2001 plus a five-byte faction splice.
        # The new module builds an entry but NEVER names the death-timer bit
        # (it forbids every non-0x070C bit by strict mask equality), so the
        # SET and FORBID censuses above are BOTH unmoved -- exactly the guard
        # that proves the third actor-entry builder is not a third timer
        # emitter.
        # Round 111: they move 7 -> 8 for NPC-HP-LINK-001 (HYP-PF-029), the
        # fourth actor-entry builder outside the spawn path.  Unlike the
        # round-99 hostile lane this one DOES name and SET the death-timer
        # bit, so the SET census above moves in the same commit -- which is
        # why both are asserted here and neither was widened.
        # Round 170: entry sites 8 -> 9 and stream sites 8 -> 11.  HYP-PF-038
        # (hostile_hp_link_hypothesis.py) adds one of each; the other two
        # stream sites are HYP-PF-032 (ground_loot_hypothesis.py), which holds
        # TWO make_runtime_remote_actors sites and ZERO actor-entry sites --
        # it rides the carrier without building an entry, which is why the
        # module census moves by one while the stream count moves by three.
        # Round swlc56: 11 -> 23, 9 -> 15, 8 -> 14.  These three pins were the
        # oldest in this file: eleven lanes landed against them while the
        # module sat excluded from the gate's client-free subset, so the first
        # thing that read them was the bridge full-pytest run of 2026-08-28,
        # which took all 19 tests in this module down at once.  The numbers
        # here are now the same four the tool guards, the report's
        # RUNTIMERES_COUNTS block carries and
        # tests/test_static_verifier_pins_cloud.py recomputes from src/ on
        # any clone -- four copies that a single drift now reddens together
        # instead of one that rots alone.
        # 23 -> 24, 15 -> 16, 14 -> 15 on 2026-08-28 (LANE-A round w0pu2i):
        # world_population_bg0015.py, the Bg0015 census, builds one entry and
        # sends one carrier -- the same single-module move bg0002 made.
        # 24 -> 25, 16 -> 17, 15 -> 16 on 2026-08-29 (LANE-E round
        # c5nwjc): world_face_frame.py rebuilds the ChooseNPC face frame
        # under the resolved census identity, so it builds one entry per
        # shipped placement and sends one carrier.  It reuses the frozen
        # serializers rather than reimplementing them, which is exactly
        # why it shows up in this census.
        # 25 -> 26 on 2026-08-29 (LANE-B round y9s0xo):
        # mob_scene_recompose.py re-encodes the collection when it splices a
        # roster override into a mid-session recompose.  ONLY the carrier
        # count moves -- the entry-builder counts below are unchanged,
        # because that module composes bodies other modules built and
        # invents none of its own.
        # 26 -> 27, 17 -> 18, 16 -> 17 on 2026-08-30 (LANE-A round 6p22bu):
        # world_population_bg0004.py, the Bg0004 (Slave Market Island)
        # census (COO-DECISION 2026-08-30T14:41+07:00), builds one entry and
        # sends one carrier -- the same single-module move bg0015 made.  Not
        # wired to any player-reachable path this round.
        # 27 -> 28, 18 -> 19, 17 -> 18 on 2026-08-31 (LANE-A round u3jo4g):
        # world_population_bg0010.py, the Bg0010 (Deep Sea Temple floor 1)
        # census (second door of the same COO-DECISION 2026-08-30T14:41+07:00
        # sequence), the same single-module move.  Not wired to any
        # player-reachable path this round either.
        # 28 -> 29, 19 -> 20, 18 -> 19 on 2026-08-31 (LANE-A round l03cgh):
        # world_population_bg0005.py, the Bg0005 (Evil Port) census (third
        # door of the same COO-DECISION 2026-08-30T14:41+07:00 sequence),
        # the same single-module move.  UNLIKE bg0004/bg0010, this module is
        # wired AND its scene's door opened in the same round that built it.
        # 29 -> 30, 20 -> 21, 19 -> 20 on 2026-08-31 (LANE-A round fx0007):
        # world_population_bg0006.py, the Bg0006 (Ocean Walled City) census
        # (fourth door of the same COO-DECISION 2026-08-30T14:41+07:00
        # sequence), the same single-module move.  Also wired AND its
        # scene's door opened in the same round that built it, same shape
        # as bg0005.
        # 30 -> 31, 21 -> 22, 20 -> 21 on 2026-08-31 (LANE-A round p4wire):
        # world_population_bg0008.py, the Bg0008 (Silver Harbour) census
        # (fifth door of the same COO-DECISION 2026-08-30T14:41+07:00
        # sequence), the same single-module move.  Also wired AND its
        # scene's door opened in the same round that built it, same shape
        # as bg0006.
        # 31 -> 32, 22 -> 23, 21 -> 22 on 2026-08-31 (LANE-A, this round):
        # world_population_bg0003.py, the Bg0003 (Spice Paradise Island)
        # census (sixth door of the same COO-DECISION 2026-08-30T14:41+07:00
        # sequence), the same single-module move.  Also wired AND its
        # scene's door opened in the same round that built it, same shape
        # as bg0008.
        # 32 -> 33, 23 -> 24, 22 -> 23 on 2026-08-31 (LANE-B, round jqxe6v):
        # field_mob_hostile_bg0015.py (COO-DECISION 2026-08-31T16:48+07:00
        # layer-1 unlock) builds one synthetic civilian actor entry per
        # Bg0015 placement for its own splice-proof function -- same
        # encoder, no new runtime.py call site.
        # 33 -> 34, 24 -> 25, 23 -> 24 on 2026-08-31 (LANE-A, round 78zayw):
        # world_population_bg0007.py, the Bg0007 (Voodoo Island) census
        # (seventh door of the same COO-DECISION 2026-08-30T14:41+07:00
        # sequence), the same single-module move.  Also wired AND its
        # scene's door opened in the same round that built it, same shape
        # as bg0003.
        # 34 -> 35, 25 -> 26, 24 -> 25 on 2026-08-31 (LANE-A, round ir0lpw):
        # world_population_bg0009.py, the Bg0009 (Death City Sea) census
        # (eighth door of the same COO-DECISION 2026-08-30T14:41+07:00
        # sequence), the same single-module move.  Also wired AND its
        # scene's door opened in the same round that built it, same shape
        # as bg0007.
        self.assertEqual(counts["src_actor_stream_call_sites"], 35)
        self.assertEqual(counts["src_actor_entry_call_sites"], 26)
        self.assertEqual(counts["src_modules_building_actor_entries"], 25)
        self.assertIn(
            "npc_hostile_hypothesis.py",
            counts["src_modules_building_actor_entries_names"],
        )
        self.assertIn(
            "npc_hp_link_hypothesis.py",
            counts["src_modules_building_actor_entries_names"],
        )
        self.assertIn(
            "field_mob_hostile_bg0015.py",
            counts["src_modules_building_actor_entries_names"],
        )
        # gap 2 is the one worth keeping a test on.  The round-85 measure -
        # the literal `current_hp = 0` - is STILL zero, because the encoder
        # passes its zero through a named constant.  That guard was about to
        # stay green while its sentence stopped being true, so both halves are
        # asserted here: the old measure and the one that actually notices.
        self.assertEqual(counts["server_call_sites_emitting_zero_current_hp"], 0)
        # Round swlc56: the named-constant census is six modules now, not one.
        # Round jop8ph-2: seven.
        # The old measure above is STILL zero -- that is the half worth
        # keeping -- and every one of the five new names passes its zero
        # through a named constant exactly as the round-86 encoder does.  The
        # tool's own guard and the report already carried all six; only this
        # copy was stale.
        self.assertEqual(counts["src_modules_passing_zero_hp_by_named_constant"],
                         ["damage_hp_link_hypothesis.py",
                          "hostile_hp_link_hypothesis.py",
                          "mob_combat.py",
                          "mob_death.py",
                          # Round jop8ph-2: the seventh.  See the tool's own
                          # comment beside this tuple -- a census that
                          # quietly widens stops being a census, so it is
                          # re-pinned rather than loosened.
                          "mob_ledger_admission.py",
                          "npc_hp_link_hypothesis.py",
                          "runtimeres_death_hypothesis.py"])

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


# Every trap mutates an in-memory copy of the client image, so none of them
# can run without the real bytes.  See tests/pf_preconditions.py.
@CLIENT_IMAGE.skip_unless_present()
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
