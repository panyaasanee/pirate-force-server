"""Pin DAMAGE-MODEL-001's numbers to the client binary they were read from.

The question this milestone answers is the one that decides how much a server
has to do: **does the client compute damage, or does it only draw what it is
told?**  The answer is a number-heavy one - a wire schema, an element stride, a
signedness, and a chain of call sites - so none of those numbers may be
hand-typed anywhere.  They live in exactly one place,
``tools/pf_damage_hit_result_static.py``, which reads them out of the bytes of
one immutable, hash-pinned client image, and this file compares what that tool
produced against the conclusions the next round would build on.

Importing the tool RUNS it.  Every one of its guards is a byte-exact assertion
against the image, so a drifted guard raises ``SystemExit`` during import and
the first test fails.  Everything after that is a check that the tool's own
report says what we think it says.

The conclusions restated here independently of the tool's prose, so that a
silent edit to either side cannot quietly change them:

  1. the wire is a tagged stream - one tag byte then a fixed-width payload -
     and the five tags this family uses are 0x0B/1, 0x12/2, 0x14/4, 0x2A/4,
     0x32/8;
  2. ``CHitResult`` (wire id 0x16F7) is a five-field header plus an array whose
     element STRIDE IS 32 BYTES, proven twice out of the bytes (`sar eax,5` and
     `add ebx,0x20`);
  3. the damage number is the element field at **+0x08**, read **SIGNED** at
     four separate `cmp dword ptr [ebx+8],0 ; jge` sites;
  4. the f32 at element **+0x18 is an ANGLE**, not a damage magnitude - it is
     the float argument of the knock/fall reaction spawner and reaches sin/cos,
     never a number widget;
  5. the on-screen number is that signed i32 displayed verbatim: the only
     arithmetic anywhere on the path is ``abs()`` (`cdq ; xor ; sub`), then
     ``sprintf`` with ``"%d"``;
  6. the client performs **no arithmetic on HP** - the attribute apply loop is a
     mask-gated verbatim ``mov`` copy, and the nineteen derived-stat accessors
     are called only from UI code.

There is also a TRAP test.  A guard that cannot fail is not a guard, so this
file mutates a COPY of a guarded byte span in memory, feeds it back through the
tool's own guard machinery, and asserts the guard rejects it.  The real binary
is never written to.  It is permanent read-only evidence and the tests re-hash
it afterwards to prove it was not touched.

These tests import nothing from ``src/``, open no socket, touch no database and
launch no GameClient.  They read one binary.

Re-pinning when a number legitimately moves (a different client build): run
``py -3 tools/pf_damage_hit_result_static.py --json`` and update this file and
the tool in the same change.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

# load_tool() makes the verifier read ../GameClient/GameClient.local.bin, a
# proprietary binary that can never be in a fresh clone, so every test that
# calls it must say so and skip without it.  See tests/pf_preconditions.py.
from pf_preconditions import CLIENT_IMAGE  # noqa: E402

TOOL = ROOT / "tools" / "pf_damage_hit_result_static.py"
CLIENT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

_TOOL_MODULE = None


def load_tool():
    """Execute the verifier once; a drifted guard becomes SystemExit here."""
    global _TOOL_MODULE
    if _TOOL_MODULE is None:
        spec = importlib.util.spec_from_file_location(
            "pf_damage_hit_result_static", TOOL)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        with redirect_stdout(io.StringIO()):
            spec.loader.exec_module(module)
        _TOOL_MODULE = module
    return _TOOL_MODULE


@contextmanager
def tampered(tool, va, mask=0xFF):
    """Swap the tool's in-memory image for a copy with one byte flipped.

    The file on disk is never opened for writing.  ``tool.data`` is restored,
    and so is the guard bookkeeping, so the tamper cannot leak into any other
    test.
    """
    offset = tool.va2off(va)
    assert offset is not None, "0x%08X is not mapped" % va
    original = tool.data
    fails_before = list(tool.FAILS)
    nguard_before = tool.NGUARD
    buf = bytearray(original)
    buf[offset] ^= mask
    tool.data = bytes(buf)
    try:
        yield
    finally:
        tool.data = original
        tool.FAILS[:] = fails_before
        tool.NGUARD = nguard_before


class ArtifactsExistTests(unittest.TestCase):
    """The tool and its evidence must ship together."""

    def test_the_tool_exists(self):
        self.assertTrue(TOOL.is_file(), TOOL)

    # Needs the client image itself, unlike the tool-exists check above.
    @CLIENT_IMAGE.skip_unless_present()
    def test_the_binary_the_tool_chose_exists_and_is_the_pinned_one(self):
        tool = load_tool()
        self.assertTrue(Path(tool.BIN).is_file(), tool.BIN)
        self.assertEqual(tool.SHA, CLIENT_SHA)
        self.assertEqual(tool.EXPECT_SHA, CLIENT_SHA)


class VerifierRunsCleanTests(unittest.TestCase):
    """Every guard in the verifier must hold against the pinned binary."""

    # Method-level guards, not a class one: the two source-only checks below
    # run fine without the client image.  See tests/pf_preconditions.py.
    @CLIENT_IMAGE.skip_unless_present()
    def test_the_verifier_imports_without_exiting(self):
        tool = load_tool()
        self.assertEqual(tool.FAILS, [], tool.FAILS)

    @CLIENT_IMAGE.skip_unless_present()
    def test_the_verifier_actually_asserted_something(self):
        self.assertGreaterEqual(load_tool().NGUARD, 200)

    @CLIENT_IMAGE.skip_unless_present()
    def test_the_reported_guard_count_matches_the_run(self):
        tool = load_tool()
        self.assertEqual(tool.RESULT["guards"], tool.NGUARD)
        self.assertEqual(tool.COUNTS["guards"], tool.NGUARD)

    def test_the_verifier_is_pure_stdlib(self):
        """The Windows release gate runs `py -3` with no third-party packages."""
        source = TOOL.read_text(encoding="utf-8")
        for banned in ("import capstone", "from capstone", "import pefile",
                       "import numpy", "import yaml"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, source)

    def test_the_verifier_never_opens_the_binary_for_writing(self):
        source = TOOL.read_text(encoding="utf-8")
        for banned in ('"wb"', "'wb'", '"r+b"', "'r+b'", '"ab"', "'ab'",
                       "os.remove", "shutil."):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, source)

    @CLIENT_IMAGE.skip_unless_present()
    def test_the_binary_on_disk_is_unchanged_after_the_run(self):
        """It is permanent read-only evidence.  Prove the run did not touch it."""
        tool = load_tool()
        digest = hashlib.sha256(Path(tool.BIN).read_bytes()).hexdigest().upper()
        self.assertEqual(digest, CLIENT_SHA)

    @CLIENT_IMAGE.skip_unless_present()
    def test_the_report_claims_nothing_about_the_original_server(self):
        tool = load_tool()
        self.assertIsNone(tool.RESULT["claims_about_original_server"])
        self.assertTrue(tool.RESULT["report_only"])
        docstring = (TOOL.read_text(encoding="utf-8").split('"""')[1])
        self.assertIn("ORIGINAL server", docstring)
        self.assertIn("report-only", docstring)
        self.assertIn("DAMAGE-MODEL-001", docstring)


# Every class below reads the pinned client image through load_tool(); a fresh
# clone cannot hold that binary.  See tests/pf_preconditions.py.
@CLIENT_IMAGE.skip_unless_present()
class TagMapTests(unittest.TestCase):
    """Conclusion 1: one tag byte then a fixed-width payload."""

    def test_the_five_tags_this_family_uses(self):
        expected = {
            "0x0B": ("u8", 1),
            "0x12": ("u16", 2),
            "0x14": ("u32", 4),
            "0x2A": ("f32", 4),
            "0x32": ("qword", 8),
        }
        live = load_tool().RESULT["tag_map"]
        self.assertEqual(sorted(live), sorted(expected))
        for tag, (name, width) in expected.items():
            with self.subTest(tag=tag):
                self.assertEqual(live[tag]["name"], name)
                self.assertEqual(live[tag]["width"], width)

    def test_no_tag_is_used_with_two_widths(self):
        live = load_tool().RESULT["tag_map"]
        widths = {t: live[t]["width"] for t in live}
        self.assertEqual(len(widths), len(live))

    def test_the_codec_and_its_tag_check_are_named(self):
        codec = load_tool().RESULT["codec"]
        self.assertEqual(codec["write"], "0x0089A600")
        self.assertEqual(codec["read"], "0x0089A640")
        self.assertEqual(codec["tag_store"], "0x0089A53B")
        self.assertEqual(codec["tag_check"], "0x0089A5BF")
        self.assertIn("stream+0x20", codec["tag_mismatch_flag"])

    def test_vector3_is_three_f32_fields_not_a_tag(self):
        codec = load_tool().RESULT["codec"]
        self.assertEqual(codec["vector3_write"], "0x005F3490")
        self.assertEqual(codec["vector3_read"], "0x005F34D0")
        self.assertNotIn("vector3", load_tool().RESULT["tag_map"])


@CLIENT_IMAGE.skip_unless_present()
class HeaderFieldTableTests(unittest.TestCase):
    """Conclusion 2a: the CHitResult header, in emission order."""

    EXPECTED = [
        ("0x32", "qword", 8, "+0x18", "0x00750059"),
        ("0x12", "u16", 2, "+0x20", "0x00750068"),
        ("0x12", "u16", 2, "+0x22", "0x00750077"),
        ("0x14", "u32", 4, "+0x24", "0x00750086"),
        ("0x0B", "u8", 1, "+0x28", "0x00750095"),
    ]

    def test_the_header_field_table_matches_exactly_and_in_order(self):
        live = load_tool().RESULT["chitresult"]["header_fields"]
        self.assertEqual(len(live), len(self.EXPECTED))
        for row, (tag, typ, width, off, va) in zip(live, self.EXPECTED):
            with self.subTest(offset=off):
                self.assertEqual(row["tag"], tag)
                self.assertEqual(row["type"], typ)
                self.assertEqual(row["width"], width)
                self.assertEqual(row["offset"], off)
                self.assertEqual(row["emit_va"], va)

    def test_the_class_identity(self):
        cls = load_tool().RESULT["chitresult"]
        self.assertEqual(cls["wire_id"], "0x16F7")
        self.assertEqual(cls["sizeof"], "0x48")
        self.assertEqual(cls["vtable"], "0x00F48AA0")
        self.assertEqual(cls["ctor"], "0x0074F940")
        self.assertEqual(cls["serializer"], "0x00750040")
        self.assertEqual(cls["inbound_handler"], "0x00750770")

    def test_the_wire_id_is_the_hash_of_the_in_image_literal(self):
        tool = load_tool()
        self.assertEqual(tool.name_id("CHitResult"), 0x16F7)
        self.assertEqual(tool.cstr(0xF0B5F8), "CHitResult")

    def test_the_array_hangs_off_plus_0x2c(self):
        cls = load_tool().RESULT["chitresult"]
        self.assertEqual(cls["array_at"], "+0x2C")
        self.assertEqual(cls["array_write"], "0x0074F5A0")
        self.assertEqual(cls["array_read"], "0x0074FF60")


@CLIENT_IMAGE.skip_unless_present()
class HitElementTableTests(unittest.TestCase):
    """Conclusion 2b: the 32-byte hit entry."""

    EXPECTED = [
        ("0x32", 8, "+0x00", "0x0074F62C", "0x0074FFCF"),
        ("0x14", 4, "+0x08", "0x0074F63E", "0x0074FFDF"),
        ("0x2A", 12, "+0x0C", "0x0074F645", "0x0074FFEA"),
        ("0x2A", 4, "+0x18", "0x0074F657", "0x0074FFFD"),
        ("0x12", 2, "+0x1C", "0x0074F666", "0x0075000D"),
    ]

    def test_the_element_field_table_matches_exactly_and_in_order(self):
        live = load_tool().RESULT["hit_element"]["fields"]
        self.assertEqual(len(live), len(self.EXPECTED))
        for row, (tag, width, off, wva, rva) in zip(live, self.EXPECTED):
            with self.subTest(offset=off):
                self.assertEqual(row["tag"], tag)
                self.assertEqual(row["width"], width)
                self.assertEqual(row["offset"], off)
                self.assertEqual(row["write_va"], wva)
                self.assertEqual(row["read_va"], rva)

    def test_the_stride_is_thirty_two_and_was_read_out_of_the_bytes(self):
        element = load_tool().RESULT["hit_element"]
        self.assertEqual(element["stride"], 32)
        self.assertEqual(load_tool().COUNTS["hit_element_stride_bytes"], 32)
        self.assertEqual(len(element["stride_proofs"]), 2)
        self.assertIn("sar eax,5", element["stride_proofs"][0])
        self.assertIn("add ebx,0x20", element["stride_proofs"][1])

    def test_the_stride_proof_bytes_are_really_there(self):
        tool = load_tool()
        # sar eax, 5   at 0x0074F5B3    and   add ebx, 0x20   at 0x0074F686
        self.assertEqual(tool.rd(0x74F5B3, 3), bytes.fromhex("c1f805"))
        self.assertEqual(tool.rd(0x74F686, 3), bytes.fromhex("83c320"))
        self.assertEqual(1 << tool.rd(0x74F5B5, 1)[0], 32)
        self.assertEqual(tool.rd(0x74F688, 1)[0], 32)

    def test_the_count_is_a_u16(self):
        element = load_tool().RESULT["hit_element"]
        self.assertEqual(element["count_tag"], "0x12")
        self.assertEqual(element["count_emit_va"], "0x0074F5C8")

    def test_the_last_field_ends_inside_the_stride(self):
        # +0x1C is a u16, so the payload ends at +0x1E; +0x1E..+0x1F is padding.
        self.assertLess(0x1C + 2, load_tool().RESULT["hit_element"]["stride"])


@CLIENT_IMAGE.skip_unless_present()
class SignedDamageFieldTests(unittest.TestCase):
    """Conclusion 3: element +0x08 is read SIGNED."""

    def test_the_damage_field_is_named_and_signed(self):
        dmg = load_tool().RESULT["hit_element"]["damage"]
        self.assertEqual(dmg["offset"], "+0x08")
        self.assertEqual(dmg["tag"], "0x14")
        self.assertEqual(dmg["signedness"], "signed i32")

    def test_all_four_signed_compare_sites_are_named(self):
        dmg = load_tool().RESULT["hit_element"]["damage"]
        self.assertEqual(
            dmg["proof_sites"],
            {
                "CHitResult 0x750919": "0x00750919",
                "CHitResult 0x7509E0": "0x007509E0",
                "CMissileHitResult 0x751219": "0x00751219",
                "CMissileHitResult 0x7512E0": "0x007512E0",
            })
        self.assertEqual(load_tool().COUNTS["signed_compare_sites"], 4)

    def test_the_branch_really_is_jge_and_not_jae(self):
        """`jge` (0F 8D / 7D) is signed; `jae` (0F 83 / 73) would be unsigned."""
        tool = load_tool()
        for va in (0x750919, 0x751219):
            with self.subTest(va=hex(va)):
                self.assertEqual(tool.rd(va, 4), bytes.fromhex("837b0800"))
                self.assertEqual(tool.rd(va + 4, 2), bytes.fromhex("0f8d"))
        for va in (0x7509E0, 0x7512E0):
            with self.subTest(va=hex(va)):
                self.assertEqual(tool.rd(va, 4), bytes.fromhex("837b0800"))
                self.assertEqual(tool.rd(va + 4, 1), bytes.fromhex("7d"))

    def test_the_field_the_ui_reads_is_the_field_the_wire_carries(self):
        tool = load_tool()
        damage_offset = tool.RESULT["hit_element"]["damage"]["offset"]
        wire = [f for f in tool.RESULT["hit_element"]["fields"]
                if f["offset"] == damage_offset]
        self.assertEqual(len(wire), 1)
        self.assertEqual(wire[0]["tag"], "0x14")
        self.assertEqual(wire[0]["width"], 4)


@CLIENT_IMAGE.skip_unless_present()
class AngleNotDamageTests(unittest.TestCase):
    """Conclusion 4: element +0x18 is a yaw angle, not a magnitude."""

    def test_the_f32_at_plus_0x18_is_declared_not_a_damage_number(self):
        angle = load_tool().RESULT["hit_element"]["angle"]
        self.assertFalse(angle["is_a_damage_number"])
        self.assertEqual(angle["offset"], "+0x18")
        self.assertEqual(angle["tag"], "0x2A")

    def test_it_goes_to_the_reaction_spawners_and_to_sin_cos(self):
        angle = load_tool().RESULT["hit_element"]["angle"]
        self.assertEqual(angle["consumer_nonmissile"], "0x0048D870")
        self.assertEqual(angle["consumer_missile"], "0x0048DBA0")
        self.assertEqual(angle["sin_cos_helper"], "0x0049C8B0")
        self.assertEqual(sorted(angle["fld_sites"]),
                         ["0x00750A42", "0x00751342"])

    def test_the_pi_constant_backing_the_angle_reading_is_really_pi(self):
        tool = load_tool()
        self.assertAlmostEqual(tool.f64(0xF0D140), 3.1415927410125732, places=12)

    def test_the_damage_offset_and_the_angle_offset_are_different_fields(self):
        element = load_tool().RESULT["hit_element"]
        self.assertNotEqual(element["damage"]["offset"], element["angle"]["offset"])


@CLIENT_IMAGE.skip_unless_present()
class ResultFlagsTests(unittest.TestCase):
    """element +0x1C is a bitfield - and the bits are deliberately unnamed."""

    def test_the_flags_field_is_a_u16_at_plus_0x1c(self):
        flags = load_tool().RESULT["hit_element"]["flags"]
        self.assertEqual(flags["offset"], "+0x1C")
        self.assertEqual(flags["tag"], "0x12")

    def test_the_knocked_literal_is_quoted_from_the_image(self):
        tool = load_tool()
        self.assertEqual(tool.wstr(0xF48B4C), "_F_KNOCKED_002")
        self.assertIn("_F_KNOCKED_002",
                      tool.RESULT["hit_element"]["flags"]["knocked_literal"])

    def test_no_semantic_bit_label_is_claimed(self):
        self.assertFalse(
            load_tool().RESULT["hit_element"]["flags"]["bit_labels_claimed"])


@CLIENT_IMAGE.skip_unless_present()
class DisplayPathTests(unittest.TestCase):
    """Conclusion 5: abs() and "%d", nothing else."""

    def test_the_path_is_the_one_we_think_it_is(self):
        path = load_tool().RESULT["display_path"]
        self.assertIn("0x00750D90", path["pickup"])
        self.assertEqual(path["dispatcher"], "0x0043FDE0")
        self.assertEqual(path["spawn"], "0x0043FBB0")
        self.assertEqual(path["ctor"], "0x00A7C010")
        self.assertEqual(path["glyph_builder"], "0x00A7EBA0")
        self.assertEqual(path["sprintf_wrapper"], "0x00896100")

    def test_the_dispatcher_is_only_ever_called_from_the_two_hit_handlers(self):
        path = load_tool().RESULT["display_path"]
        self.assertEqual(path["dispatcher_call_sites"],
                         ["0x00750DAA", "0x00750E43", "0x00751105", "0x0075161F"])
        self.assertEqual(load_tool().COUNTS["fx_dispatcher_call_sites"], 4)

    def test_the_value_is_stored_verbatim_then_printed_with_percent_d(self):
        path = load_tool().RESULT["display_path"]
        self.assertIn("mov [esi+0xF8], eax", path["value_store"])
        self.assertIn("'%d'", path["format_literal"])
        self.assertEqual(load_tool().cstr(0xF14A94), "%d")

    def test_abs_is_the_only_arithmetic_and_the_scale_is_one(self):
        tool = load_tool()
        self.assertEqual(tool.RESULT["display_path"]["scaling_applied"], "none")
        self.assertEqual(
            tool.RESULT["negatives"]["arithmetic_on_the_displayed_number"],
            "abs() only")
        self.assertEqual(tool.COUNTS["damage_field_arithmetic_applied"], "abs")
        self.assertEqual(tool.COUNTS["damage_field_scale_factor"], 1)

    def test_the_abs_sequence_bytes_are_contiguous_and_exact(self):
        """mov eax,[esp+0x68] ; cdq ; xor eax,edx ; sub eax,edx - 9 bytes."""
        tool = load_tool()
        self.assertEqual(tool.span(0xA7EBFB, 0xA7EC04),
                         bytes.fromhex("8b4424689933c22bc2"))
        self.assertEqual(tool.rd(0xA7EBFF, 1), b"\x99")        # cdq
        self.assertEqual(tool.rd(0xA7EC00, 2), b"\x33\xc2")    # xor eax, edx
        self.assertEqual(tool.rd(0xA7EC02, 2), b"\x2b\xc2")    # sub eax, edx


@CLIENT_IMAGE.skip_unless_present()
class NoArithmeticNegativeTests(unittest.TestCase):
    """Conclusion 6: the client computes nothing and never mutates HP."""

    def test_the_two_headline_negatives_are_stated_flatly(self):
        neg = load_tool().RESULT["negatives"]
        self.assertFalse(neg["client_computes_damage"])
        self.assertFalse(neg["client_mutates_hp_from_a_hit"])

    def test_every_function_on_the_path_is_byte_frozen(self):
        tool = load_tool()
        frozen = tool.RESULT["negatives"]["byte_frozen_spans"]
        self.assertEqual(len(frozen), tool.COUNTS["byte_frozen_path_spans"])
        self.assertGreaterEqual(len(frozen), 12)
        for entry in frozen:
            with self.subTest(span=entry["name"]):
                lo = int(entry["lo"], 16)
                hi = int(entry["hi"], 16)
                self.assertEqual(tool.span_sha(lo, hi), entry["sha256"])

    def test_the_multiply_divide_encodings_are_absent_where_claimed(self):
        tool = load_tool()
        for entry in tool.RESULT["negatives"]["muldiv_encodings_absent_from"]:
            lo = int(entry["lo"], 16)
            hi = int(entry["hi"], 16)
            blob = tool.span(lo, hi)
            for hexpat in entry["encodings"]:
                with self.subTest(span=entry["span"], op=hexpat):
                    self.assertNotIn(bytes.fromhex(hexpat), blob)

    def test_the_attribute_apply_loop_is_a_verbatim_copy(self):
        tool = load_tool()
        described = tool.RESULT["negatives"]["attribute_apply_loop"]
        self.assertIn("0x00464436..0x004644E0", described)
        self.assertIn("verbatim", described)
        self.assertEqual(tool.COUNTS["attr_apply_loop_arithmetic_ops"], 0)
        blob = tool.span(0x464436, 0x4644E0)
        # bit 0x40 -> +0x44 (current HP) and the sign bit -> +0x48 (max HP),
        # both copied with a plain `mov`.
        self.assertIn(bytes.fromhex("a84075068b4e44894f44"), blob)
        self.assertIn(bytes.fromhex("84c078068b5648895748"), blob)
        # and no add/sub into either of them
        for hexpat in ("014144", "294144", "014644", "294644",
                       "014148", "294148", "014648", "294648"):
            with self.subTest(op=hexpat):
                self.assertNotIn(bytes.fromhex(hexpat), blob)

    def test_the_hit_handler_never_reads_or_writes_hp(self):
        counts = load_tool().COUNTS
        self.assertEqual(counts["hp_writes_in_chitresult_handler"], 0)
        self.assertEqual(counts["hp_reads_in_chitresult_handler"], 0)

    def test_the_derived_stat_accessors_are_ui_only(self):
        tool = load_tool()
        self.assertTrue(
            tool.RESULT["negatives"]["derived_stat_accessors_are_ui_only"])
        self.assertEqual(tool.COUNTS["derived_stat_accessors"], 19)
        self.assertEqual(
            tool.COUNTS["derived_stat_accessor_callers_in_combat_code"], 0)

    def test_no_accessor_caller_lives_in_a_combat_function(self):
        """Recomputed here from the tool's own call index, not from its prose."""
        tool = load_tool()
        for accessor, callers in tool.DERIVED_STAT_ACCESSORS.items():
            with self.subTest(accessor=hex(accessor)):
                self.assertEqual(tool.calls_to(accessor), sorted(callers))
                for caller in callers:
                    for lo, hi in tool.COMBAT_RANGES:
                        self.assertFalse(lo <= caller < hi,
                                         "%s is inside 0x%08X..0x%08X"
                                         % (hex(caller), lo, hi))


@CLIENT_IMAGE.skip_unless_present()
class DyingAndReviveTests(unittest.TestCase):
    """The downed phase, its one button, and the request-only revive verb."""

    def test_duration_dying_is_an_integer_config_with_one_reader(self):
        tool = load_tool()
        dying = tool.RESULT["dying_and_revive"]
        self.assertEqual(dying["duration_dying_global"], "0x0102249C")
        self.assertEqual(dying["duration_dying_default"], 20)
        self.assertEqual(dying["duration_dying_units"], "seconds, counting down")
        self.assertEqual(dying["duration_dying_sole_reader"], "0x0044A572")
        self.assertEqual(tool.COUNTS["duration_dying_text_references"], 2)

    def test_the_gate_constant_is_a_double(self):
        tool = load_tool()
        self.assertEqual(tool.f64(0xF092D0), 0.5)
        self.assertIn("double",
                      tool.RESULT["dying_and_revive"]["main_dead_gate_constant"])

    def test_dying_and_dead_are_two_different_predicates(self):
        dying = load_tool().RESULT["dying_and_revive"]
        self.assertIn("+0x40", dying["is_dying"])
        self.assertIn("timer > 0", dying["is_dying"])
        self.assertIn("+0x3C", dying["is_dead"])
        self.assertIn("timer <= 0", dying["is_dead"])

    def test_the_downed_window_and_the_death_window_are_different(self):
        dying = load_tool().RESULT["dying_and_revive"]
        self.assertIn("Main_Dead", dying["downed_window"])
        self.assertIn("Common_Death", dying["death_window"])
        self.assertNotEqual(dying["downed_window"], dying["death_window"])

    def test_the_one_button_sends_action_0xea7c(self):
        tool = load_tool()
        dying = tool.RESULT["dying_and_revive"]
        self.assertIn("BUTTON_DIE", dying["downed_button"])
        self.assertIn("0xEA7C", dying["downed_button_action_id"])
        self.assertEqual(tool.rd(0x518493, 7),
                         bytes.fromhex("c740307cea0000"))

    def test_relive_vital_is_request_only(self):
        tool = load_tool()
        relive = tool.RESULT["dying_and_revive"]["relive_vital"]
        self.assertEqual(relive["id"], "0x1AD4")
        self.assertIn("i8 mode @+0x14", relive["wire"])
        self.assertIn("0x00710440", relive["inbound_slot"])
        self.assertEqual(len(relive["producers"]), 3)
        self.assertEqual(tool.COUNTS["relive_vital_inbound_handlers"], 0)


@CLIENT_IMAGE.skip_unless_present()
class TrapTests(unittest.TestCase):
    """A guard that cannot fail is not a guard.

    Each of these flips ONE byte in an in-memory COPY of the image and asserts
    the tool's own guard machinery rejects it.  The file on disk is never
    written; ``tampered`` restores ``tool.data`` and the guard bookkeeping.
    """

    def test_flipping_the_abs_instruction_breaks_its_byte_guard(self):
        tool = load_tool()
        pinned = "8b4424689933c22bc2508d44243c50e8f174e1ff"
        self.assertEqual(tool.rd(0xA7EBFB, len(pinned) // 2),
                         bytes.fromhex(pinned))
        with tampered(tool, 0xA7EC02):          # the `sub eax, edx` of abs()
            self.assertNotEqual(tool.rd(0xA7EBFB, len(pinned) // 2),
                                bytes.fromhex(pinned))
            self.assertFalse(tool.gbytes(0xA7EBFB, pinned, "trap"))
        # restored
        self.assertEqual(tool.rd(0xA7EBFB, len(pinned) // 2),
                         bytes.fromhex(pinned))
        self.assertEqual(tool.FAILS, [])

    def test_flipping_a_byte_anywhere_in_a_frozen_span_breaks_its_hash(self):
        tool = load_tool()
        frozen = {e["name"]: e
                  for e in tool.RESULT["negatives"]["byte_frozen_spans"]}
        entry = frozen["hit-reaction FX dispatcher 0x43FDE0"]
        lo, hi = int(entry["lo"], 16), int(entry["hi"], 16)
        self.assertEqual(tool.span_sha(lo, hi), entry["sha256"])
        # pick a byte in the middle of the span, far from any pinned instruction
        with tampered(tool, lo + (hi - lo) // 2):
            self.assertNotEqual(tool.span_sha(lo, hi), entry["sha256"])
            self.assertFalse(tool.gspan(lo, hi, entry["sha256"], "trap"))
        self.assertEqual(tool.span_sha(lo, hi), entry["sha256"])
        self.assertEqual(tool.FAILS, [])

    def test_smuggling_a_mulss_into_a_zero_arithmetic_span_is_caught(self):
        """Splice F3 0F 59 into the FX dispatcher copy and re-run the absence
        guard - it must reject."""
        tool = load_tool()
        lo, hi = 0x43FDE0, 0x440164
        self.assertNotIn(bytes.fromhex("f30f59"), tool.span(lo, hi))
        offset = tool.va2off(lo + 0x40)
        original = tool.data
        fails_before, nguard_before = list(tool.FAILS), tool.NGUARD
        buf = bytearray(original)
        buf[offset:offset + 3] = bytes.fromhex("f30f59")
        tool.data = bytes(buf)
        try:
            self.assertIn(bytes.fromhex("f30f59"), tool.span(lo, hi))
            self.assertFalse(tool.gabsent(lo, hi, "f30f59", "trap"))
        finally:
            tool.data = original
            tool.FAILS[:] = fails_before
            tool.NGUARD = nguard_before
        self.assertNotIn(bytes.fromhex("f30f59"), tool.span(lo, hi))
        self.assertEqual(tool.FAILS, [])

    def test_flipping_the_stride_byte_breaks_the_stride_proof(self):
        tool = load_tool()
        self.assertEqual(tool.rd(0x74F688, 1)[0], 32)
        with tampered(tool, 0x74F688, mask=0x30):   # 0x20 -> 0x10
            self.assertNotEqual(tool.rd(0x74F688, 1)[0], 32)
            self.assertFalse(tool.gbytes(0x74F686, "83c320", "trap"))
        self.assertEqual(tool.rd(0x74F688, 1)[0], 32)
        self.assertEqual(tool.FAILS, [])

    def test_the_real_binary_survived_every_trap(self):
        tool = load_tool()
        self.assertEqual(hashlib.sha256(tool.data).hexdigest().upper(),
                         CLIENT_SHA)
        self.assertEqual(
            hashlib.sha256(Path(tool.BIN).read_bytes()).hexdigest().upper(),
            CLIENT_SHA)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
