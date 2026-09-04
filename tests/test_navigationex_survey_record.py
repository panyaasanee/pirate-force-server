"""Byte-for-byte fixture tests for the `NavigationEx_AddSurveyDataVtial`
nested record encoder (RE-227's pinned field layout), and a repository-wide
grep guard proving it is called from no send path.

LANE-A, COO-DECISION 20260904_0747 item 3(b): build the encoder from bytes
RE-227 already pinned, never wire it to send until GT-228 measures real
island XYZ.
"""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "current"))

import pf_login_game_server_v141 as legacy  # noqa: E402
from pirateforce_foundation import navigationex_survey_record as survey  # noqa: E402


def _hand_built_record(fields: survey.SurveyRecordFields) -> bytes:
    """The same 9 fields, assembled with raw struct packing instead of the
    frozen tag helpers -- an independent second construction so a bug
    shared between this module and its own encoder cannot hide (same
    discipline as the sibling walker's fixture-rot guards).
    """
    return (
        bytes([0x0B, survey.SURVEY_RECORD_KIND])
        + bytes([0x12]) + struct.pack("<H", fields.survey_id & 0xFFFF)
        + bytes([0x12]) + struct.pack("<H", fields.unmeasured_0x14 & 0xFFFF)
        + bytes([0x12]) + struct.pack("<H", fields.unmeasured_0x16 & 0xFFFF)
        + bytes([0x2A]) + struct.pack("<f", fields.x)
        + bytes([0x2A]) + struct.pack("<f", fields.y)
        + bytes([0x2A]) + struct.pack("<f", fields.z)
        + bytes([0x32]) + struct.pack("<Q", fields.unmeasured_0x28 & 0xFFFFFFFFFFFFFFFF)
        + bytes([0x12]) + struct.pack("<H", fields.unmeasured_0x30 & 0xFFFF)
    )


class EncodeSurveyRecordTests(unittest.TestCase):
    def test_matches_an_independently_hand_built_fixture(self):
        fields = survey.SurveyRecordFields(
            survey_id=0x1234, x=6077.9, y=1012.4, z=186.0,
            unmeasured_0x14=0xAAAA, unmeasured_0x16=0xBBBB,
            unmeasured_0x28=0x1122334455667788, unmeasured_0x30=0xCCCC,
        )
        self.assertEqual(
            survey.encode_survey_record(legacy, fields),
            _hand_built_record(fields),
        )

    def test_default_unmeasured_fields_are_zero_not_a_guessed_value(self):
        fields = survey.SurveyRecordFields(survey_id=1, x=0.0, y=0.0, z=0.0)
        record = survey.encode_survey_record(legacy, fields)
        self.assertEqual(record, _hand_built_record(fields))
        self.assertEqual(fields.unmeasured_0x14, 0)
        self.assertEqual(fields.unmeasured_0x16, 0)
        self.assertEqual(fields.unmeasured_0x28, 0)
        self.assertEqual(fields.unmeasured_0x30, 0)

    def test_length_matches_the_fixed_offset_span_re_227_pinned(self):
        # +0x10 .. +0x32 (the last field's value ends there) is 0x22 = 34
        # bytes of RECORD MEMORY, but the WIRE encoding also carries one tag
        # byte per field (9 fields), so wire length is record span + fields
        # bytes already counted as tag bytes -- checked directly against the
        # module's own declared constant instead of re-deriving the value
        # differently here, so a future field addition must update both
        # together.
        fields = survey.SurveyRecordFields(survey_id=1, x=1.0, y=2.0, z=3.0)
        self.assertEqual(
            len(survey.encode_survey_record(legacy, fields)), survey.RECORD_LEN,
        )

    def test_the_record_kind_byte_is_the_proven_value_one(self):
        # RE-227 item 2: the contact tick selects a record only when byte
        # +0x10 == 1.  A record built with any other kind would never be
        # read by that tick -- pinned here so a future edit cannot drift it.
        self.assertEqual(survey.SURVEY_RECORD_KIND, 1)
        fields = survey.SurveyRecordFields(survey_id=1, x=0.0, y=0.0, z=0.0)
        record = survey.encode_survey_record(legacy, fields)
        self.assertEqual(record[0], 0x0B)
        self.assertEqual(record[1], 1)

    def test_the_survey_id_field_is_the_one_enterinstance_echoes(self):
        # Cross-checked against the sibling inbound module's own fixed
        # shape (`12 <u16 LE> 0B 06`): the byte this record writes at the
        # survey_id field position must be readable the same way that
        # module decodes its confirm frame, since the client is proven
        # (RE-227) to copy this exact u16 unchanged into that frame.
        from pirateforce_foundation.lane_hooks import lane_a_enter_instance_log as enter_instance

        for survey_id in (0, 1, 0x1234, 0xFFFF):
            fields = survey.SurveyRecordFields(survey_id=survey_id, x=0.0, y=0.0, z=0.0)
            record = survey.encode_survey_record(legacy, fields)
            # record[0:2] = kind tag(0x0B) + value; record[2] = the
            # survey_id field's own tag(0x12); record[3:5] = its u16 LE
            # value.
            self.assertEqual(record[2], 0x12)
            self.assertEqual(
                int.from_bytes(record[3:5], "little"), survey_id,
            )
            # And decoding a hand-built EnterInstance confirm body carrying
            # the same id round-trips through the sibling module.
            confirm_body = legacy.u16tag(0x12, survey_id) + legacy.u8tag(0x0B, 6)
            self.assertEqual(enter_instance.decode_opaque(confirm_body), survey_id)

    def test_the_xyz_triple_round_trips(self):
        fields = survey.SurveyRecordFields(survey_id=1, x=-4418.0, y=-6261.2, z=186.0)
        record = survey.encode_survey_record(legacy, fields)
        # Three f32 fields, each tag(1) + value(4), sitting after the kind
        # byte(2) and three u16 fields(3*3=9): offset 2+9 = 11.
        offset = 11
        self.assertEqual(record[offset], 0x2A)
        got_x = struct.unpack("<f", record[offset + 1:offset + 5])[0]
        self.assertEqual(record[offset + 5], 0x2A)
        got_y = struct.unpack("<f", record[offset + 6:offset + 10])[0]
        self.assertEqual(record[offset + 10], 0x2A)
        got_z = struct.unpack("<f", record[offset + 11:offset + 15])[0]
        self.assertAlmostEqual(got_x, fields.x, places=1)
        self.assertAlmostEqual(got_y, fields.y, places=1)
        self.assertAlmostEqual(got_z, fields.z, places=1)


class EncodeAddSurveyDataOuterTests(unittest.TestCase):
    def test_wraps_the_record_in_the_frozen_make_runtime_vitals_envelope(self):
        fields = survey.SurveyRecordFields(survey_id=0x1234, x=1.0, y=2.0, z=3.0)
        record = survey.encode_survey_record(legacy, fields)
        pc, frame = survey.encode_add_survey_data_outer(
            legacy, msg_id=0xDEAD, vital_version=7, fields=fields,
        )
        expected_pc, expected_frame = legacy.make_runtime_vitals(
            [(0xDEAD, 7, record)],
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertIn(record, pc)

    def test_the_envelope_carries_the_trailing_derived_class_mask(self):
        """The two bytes GT-010 died without.  Chief, round `t7bsfx`/R342,
        pf-adversary D1.

        `make_runtime_vital` (SINGULAR) omits the `0B 00` derived-class
        change mask that `make_runtime_vitals` appends, and the frozen
        composer's own comment says omitting it makes the client over-read
        the collection response and raise `ErrorData=28317` -- measured
        closing the client in R306.  Pinned as a byte fact rather than left
        to the composer's name, so a future tidy-up back to the singular
        call is a red test and not a spent attended round.
        """
        fields = survey.SurveyRecordFields(survey_id=1, x=0.0, y=0.0, z=0.0)
        pc, _frame = survey.encode_add_survey_data_outer(
            legacy, msg_id=0xDEAD, vital_version=0, fields=fields,
        )
        self.assertTrue(
            pc.endswith(legacy.u8tag(0x0B, 0)),
            "the AddSurveyData envelope must end with the derived-class "
            "change mask (0B 00); it does not",
        )
        singular_pc, _ = legacy.make_runtime_vital(
            0xDEAD, 0, survey.encode_survey_record(legacy, fields),
        )
        self.assertEqual(pc, singular_pc + legacy.u8tag(0x0B, 0))

    def test_msg_id_has_no_default_the_caller_must_supply_one(self):
        import inspect

        sig = inspect.signature(survey.encode_add_survey_data_outer)
        self.assertIs(sig.parameters["msg_id"].default, inspect.Parameter.empty)


class R313CaptureParityTests(unittest.TestCase):
    """The static-parser comparison COO-DECISION 20260905_0251 / the R313
    letter (`pf_bridge/notes_to_chief/20260905_0212_KA1A-R313-RESULTS-*`)
    asked for: does this encoder's output match the actual bytes the server
    sent and the client rejected with `ErrorData=50351`?

    R313's own prose calls the frame "70 B"; the hex it pastes is 60 bytes.
    pf-adversary (this round) caught a first draft here that called that a
    prose slip -- WRONG.  `encode_add_survey_data_outer` returns a
    `(pc, frame)` pair, same as every other frozen composer in this
    project: `pc` is the pre-compression content (60 bytes here) and
    `frame` is `frame_pc(pc)` -- `current/pf_login_game_server_v141.py`'s
    `MAGIC + varint(len(compressed)) + snappy_raw_literal(pc)` wrapper.
    Computed directly below: `len(frame) == 70`.  Both numbers in R313's
    letter are correct; they name two different layers of the same send,
    and this class pins both rather than picking one and calling the other
    wrong.
    """

    # `SURVEY2_DOCK153_INITIAL`, console line 4168, R313 (2026-09-05T02:0x).
    _R313_DOCK153_INITIAL_HEX = (
        "12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 AF C4 0B 00 "
        "0B 01 12 02 00 12 00 00 12 00 00 2A 66 6E AF C5 2A 00 14 82 45 "
        "2A 00 00 3A 43 32 00 00 00 00 00 00 00 00 12 00 00 0B 00"
    )

    def test_the_pasted_hex_is_the_60_byte_pc_not_the_70_byte_frame(self):
        raw = bytes.fromhex(self._R313_DOCK153_INITIAL_HEX.replace(" ", ""))
        self.assertEqual(len(raw), 60)

    def test_the_encoder_reproduces_the_r313_capture_byte_for_byte(self):
        # Field values read off the same letter's own decode line, not
        # re-guessed: msg_id 0xC4AF, vital_version 0, survey_id 2 (DOCK153),
        # XYZ (-5613.8, 4162.5, 186.0), every unmeasured field 0.
        fields = survey.SurveyRecordFields(
            survey_id=2, x=-5613.8, y=4162.5, z=186.0,
        )
        pc, frame = survey.encode_add_survey_data_outer(
            legacy, msg_id=0xC4AF, vital_version=0, fields=fields,
        )
        captured = bytes.fromhex(
            self._R313_DOCK153_INITIAL_HEX.replace(" ", "")
        )
        self.assertEqual(
            pc, captured,
            "this encoder no longer reproduces the exact bytes R313 sent "
            "and the client rejected with ErrorData=50351 -- if this ever "
            "goes red, the encoder changed, not the finding below",
        )
        # The letter's other number: the actual compressed wire frame this
        # same call would have gone out as is 70 bytes, matching R313's
        # prose exactly. Pinned so nobody re-reads "70 B" as a second slip.
        self.assertEqual(len(frame), 70)

    def test_therefore_the_50351_rejection_is_not_an_encoder_vs_re227_mismatch(self):
        # The point of the two tests above: this encoder already implements
        # RE-227's pinned layout tag-for-tag (see the module docstring and
        # `EncodeSurveyRecordTests` above), and it reproduces exactly what
        # R313 sent. So whatever the client's real reader disagrees with is
        # NOT visible to a comparison against RE-227's own findings -- it
        # must live in one of the four fields RE-227 itself called
        # UNMEASURED (`unmeasured_0x14`, `unmeasured_0x16`,
        # `unmeasured_0x28`, `unmeasured_0x30`), in `vital_version`, or in a
        # field RE-227's static pass never reached at all.  Resolving which
        # needs either the RE runner's own machine (this environment has no
        # copy of the shipped client image -- deliberately NOT spelled with
        # its filename here: the Windows gate drops any tests/ module that
        # contains that literal from its selection, and spelling it out in
        # this comment is exactly what turned #785 red, see the class
        # docstring) or another attended trial that varies one field at a
        # time -- this test only closes off the one explanation that WAS
        # checkable from committed artifacts.
        self.assertEqual(
            {"unmeasured_0x14", "unmeasured_0x16", "unmeasured_0x28",
             "unmeasured_0x30"},
            {
                name for name in survey.SurveyRecordFields._fields
                if name.startswith("unmeasured_")
            },
        )


class NotWiredToAnySendPathTests(unittest.TestCase):
    def test_no_python_file_anywhere_in_this_repository_imports_this_module(self):
        # A grep guard, not a claim about intent: proves the nonclaim in
        # this module's own docstring stays true as the tree grows.
        #
        # pf-adversary (this round): the first draft of this guard scanned
        # only `src/`, which is exactly where this project's OTHER real
        # send paths do not all live -- `tools/pf_*_headless_replay.py`
        # scripts open real sockets and send real frames
        # (`grep -l "socket.socket\|sendall" tools/*.py` finds several),
        # and a mutation adding an import of this module to one of them
        # left the old, narrower guard green.  Scanning the WHOLE
        # repository (this file's own module and this test file excepted)
        # is what actually backs the docstring's "ANYWHERE IN THIS
        # REPOSITORY" claim.
        #
        # GT-228 (R308, PASS, 2026-09-04) measured real island XYZ, which is
        # the exact condition this guard's own assertion message names as
        # the day this changes -- COO-DECISION 20260904_1345 item 3(b) then
        # ordered the trial composer that reads this encoder,
        # `world_m2_provisioning_trial.py`.  That module is still not a send
        # path itself (it opens no socket, calls no `sendall`; see its own
        # `NotWiredToAnySendPathTests` in `test_world_m2_provisioning_trial
        # .py`), so it and its test file join the exclusion below -- the
        # first widening of this guard since it was written, and the reason
        # is on the record rather than a silent loosening.
        # Excluded by RELATIVE PATH, not basename (pf-adversary, this round):
        # a basename-only exclusion is evaded by any file anywhere in the
        # tree -- a duplicate, a scratch copy under tools/ -- that happens to
        # share one of these names, even one that opens a real socket.
        excluded = {
            "src/pirateforce_foundation/navigationex_survey_record.py",
            "tests/test_navigationex_survey_record.py",
            "src/pirateforce_foundation/world_m2_provisioning_trial.py",
            "tests/test_world_m2_provisioning_trial.py",
        }
        hits = []
        for path in ROOT.rglob("*.py"):
            if ".git" in path.parts:
                continue
            rel = str(path.relative_to(ROOT))
            if rel.replace("\\", "/") in excluded:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "navigationex_survey_record" in text:
                hits.append(rel)
        self.assertEqual(
            hits, [],
            "navigationex_survey_record must not be imported by any send "
            f"path (world_m2_provisioning_trial.py excepted); found: {hits}",
        )


if __name__ == "__main__":
    unittest.main()
