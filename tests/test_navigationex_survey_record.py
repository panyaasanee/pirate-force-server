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

    🔴 WHAT THIS CLASS IS NOT.  The commit R313 booted and this one differ
    by no executable line of `navigationex_survey_record.py` (docstrings
    only), so the "capture" below is this encoder's own output.  Comparing
    them is a NO-DRIFT PIN -- it cannot fail unless someone edits the
    encoder, and it is NOT evidence that the encoder is right.  The client
    rejected these exact bytes.  ~~an earlier version of this docstring
    concluded "so the rejection is not an encoder mismatch"~~ IS STRUCK
    (pf-adversary, round `f03s5f`, D2).

    ON THE TWO SIZES.  `encode_add_survey_data_outer` returns `(pc, frame)`:
    `pc` is the pre-compression content (60 bytes here) and `frame` is
    `frame_pc(pc)` -- v141's `MAGIC + varint(len(compressed)) +
    snappy_raw_literal(pc)` wrapper, a fixed 10-byte header, so
    `len(frame) == 70` is arithmetic on `len(pc) == 60` and carries no
    independent information about R313.  ~~"Both numbers in R313's letter
    are correct; they name two different layers"~~ IS STRUCK (pf-adversary
    D3): the letter labels the 60-byte hex block itself "70 B" and never
    names two layers.  The pc/frame reading is THIS round's reconstruction
    of how a 60-byte paste could be captioned 70, and it is plausible, not
    established -- a transcription that dropped bytes on the way into the
    letter would look identical from here and is not excluded.
    """

    # `SURVEY2_DOCK153_INITIAL`, console line 4168, R313 (2026-09-05T02:0x).
    _R313_DOCK153_INITIAL_HEX = (
        "12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 AF C4 0B 00 "
        "0B 01 12 02 00 12 00 00 12 00 00 2A 66 6E AF C5 2A 00 14 82 45 "
        "2A 00 00 3A 43 32 00 00 00 00 00 00 00 00 12 00 00 0B 00"
    )

    def test_the_pasted_hex_is_60_bytes_whatever_the_letter_captions_it(self):
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
        # The compressed frame this same call goes out as is 70 bytes.
        # Derived, not independent: frame_pc adds a fixed 10-byte header,
        # so this restates len(pc) == 60.  Kept only so the wrapper cannot
        # change size unnoticed.
        self.assertEqual(len(frame), 70)

    def test_the_four_fields_this_module_calls_unmeasured_are_exactly_these(self):
        # A FIELD-NAME PIN, and nothing more.  ~~an earlier name for this
        # test ("therefore the 50351 rejection is not an encoder vs RE-227
        # mismatch") claimed a conclusion its body cannot reach~~ IS STRUCK
        # (pf-adversary, round `f03s5f`, D4): the assertion below is green
        # for any encoder bug and any client behaviour whatsoever.  What it
        # does buy: the set of fields RE-227 itself called UNMEASURED
        # (`unmeasured_0x14`, `unmeasured_0x16`, `unmeasured_0x28`,
        # `unmeasured_0x30`) cannot silently grow or shrink.  Those four,
        # plus `vital_version`, plus the outer `0x0B` field the serializer
        # table carries (see the module docstring), are where the client's
        # disagreement can live -- and in a
        # field RE-227's static pass never reached at all.  Resolving which
        # needs either the RE runner's own machine (this environment has no
        # copy of the shipped client image -- deliberately NOT spelled with
        # its filename here: the Windows gate drops any tests/ module that
        # contains that literal from its selection, and spelling it out in
        # this comment is exactly what turned #785 red -- gate log for
        # 7caacd7, and the round file
        # pf_bridge/rounds/A_20260905_0422_f03s5f_*) or another attended
        # trial that varies one field at a
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


class OuterLeadingByteTests(unittest.TestCase):
    """The field `pf_bridge/external/PF_SERIALIZER_FIELDS.tsv` carries for
    this class's OUTER serializer, and R313's frame did not (round
    `f03s5f`, pf-adversary D1).

    The table (lines 6377-6388, same span `[0x00733570,0x00733614)` and same
    SHA RE-227 cites) records a `0x0B`-tagged field of length 1 at
    `STACK@0x00733570+0x18`, gate `ALWAYS`, on the read side and the write
    side both.  Its VALUE is measured nowhere, so the composer refuses to
    pick one: `None` (the default) keeps the exact bytes R313 sent, and a
    caller who wants to try a value has to write it down.
    """

    _FIELDS = survey.SurveyRecordFields(survey_id=2, x=-5613.8, y=4162.5, z=186.0)

    def test_default_is_byte_identical_to_what_r313_sent(self):
        with_default, _ = survey.encode_add_survey_data_outer(
            legacy, msg_id=0xC4AF, vital_version=0, fields=self._FIELDS,
        )
        explicit_none, _ = survey.encode_add_survey_data_outer(
            legacy, msg_id=0xC4AF, vital_version=0, fields=self._FIELDS,
            outer_leading_byte=None,
        )
        captured = bytes.fromhex(
            R313CaptureParityTests._R313_DOCK153_INITIAL_HEX.replace(" ", "")
        )
        self.assertEqual(with_default, captured)
        self.assertEqual(explicit_none, captured)

    def test_a_value_inserts_one_0b_field_before_the_record_and_nothing_else(self):
        base, _ = survey.encode_add_survey_data_outer(
            legacy, msg_id=0xC4AF, vital_version=0, fields=self._FIELDS,
        )
        for value in (0, 1):
            with self.subTest(value=value):
                got, frame = survey.encode_add_survey_data_outer(
                    legacy, msg_id=0xC4AF, vital_version=0,
                    fields=self._FIELDS, outer_leading_byte=value,
                )
                # Exactly two bytes longer, and the two extra bytes are the
                # 0x0B tag and the value, sitting after the vital header
                # (which ends at offset 20, pinned by the reader-order test
                # below) and before the record's own kind byte.
                self.assertEqual(len(got), len(base) + 2)
                self.assertEqual(got[:20], base[:20])
                self.assertEqual(got[20:22], bytes([0x0B, value]))
                self.assertEqual(got[22:], base[20:])
                self.assertEqual(len(frame), len(legacy.frame_pc(got)))

    def test_the_record_is_still_the_re227_record_at_the_right_offset(self):
        got, _ = survey.encode_add_survey_data_outer(
            legacy, msg_id=0xC4AF, vital_version=0, fields=self._FIELDS,
            outer_leading_byte=1,
        )
        record = survey.encode_survey_record(legacy, self._FIELDS)
        self.assertEqual(len(record), survey.RECORD_LEN)
        # By index, not `assertIn`: a position-blind check would pass if the
        # record moved (pf-adversary pass 2).  Header 20 bytes + the two
        # outer bytes, then the record, then the trailing change mask.
        self.assertEqual(got[22:22 + survey.RECORD_LEN], record)
        self.assertEqual(got[22 + survey.RECORD_LEN:], bytes([0x0B, 0]))

    def test_the_value_with_a_precedent_is_named_and_it_is_one(self):
        """`0` and `1` are not symmetric candidates (pf-adversary pass 2).

        For the same construct -- a presence byte guarding a nested object
        -- v141's `make_v137_marker1_transport_probe` is a frame the real
        client ACCEPTED, and it sends `0B 01` before the present target and
        `0B 00` for the absent ones.  Read out of the frozen module here
        rather than asserted from prose, so the precedent goes red if that
        composer ever changes shape.
        """
        self.assertEqual(survey.OUTER_PRESENCE_PRESENT, 1)
        pc, _ = legacy.make_v137_marker1_transport_probe()
        # The vital header ends at 20 (`0B 04` there is TeleportVital's
        # vital_version 4, not a payload byte); the payload then opens with
        # `0B 02`, the change mask, and `0B 01`, the presence byte for a
        # target that IS there.
        self.assertEqual(pc[18:20], bytes([0x0B, 4]))
        self.assertEqual(pc[20:24], bytes([0x0B, 2, 0x0B, 1]))

    def test_a_value_that_does_not_fit_a_byte_is_refused_not_truncated(self):
        """256 silently encoding as `0B 00` would send the value that means
        "no object follows" while the console line said 256, in a trial
        where 0-vs-1 is the entire question (pf-adversary pass 2).
        """
        for bad in (256, -1, 1 << 20):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    survey.encode_add_survey_data_outer(
                        legacy, msg_id=0xC4AF, vital_version=0,
                        fields=self._FIELDS, outer_leading_byte=bad,
                    )
        for bad in (True, False, 1.0, "1", b"\x01"):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    survey.encode_add_survey_data_outer(
                        legacy, msg_id=0xC4AF, vital_version=0,
                        fields=self._FIELDS, outer_leading_byte=bad,
                    )


class ErrorDataIsAMessageIdTests(unittest.TestCase):
    """R313's dialog number is an id, not an error code (round `f03s5f`).

    The rule is this repository's own, already written down for the other
    number every wire module here has paid for: "28317 = 0x6E9D =
    GSCN_RunTimeProtocolRes, the class id itself"
    (`delete_actor_hypothesis.py:32`, `mob_loot.py:159`).  Nobody had
    applied it to 50351.  These tests do the arithmetic once, in a place
    that goes red if either id ever moves, so the next attended round can
    read a dialog number off the screen and know WHERE the client's reader
    stopped without re-deriving anything.
    """

    def test_the_r313_dialog_number_is_this_vitals_own_id(self):
        self.assertEqual(
            survey.R313_SURVEY_DIALOG_ERRORDATA,
            survey.NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID,
            "50351 is 0xC4AF -- if this is ever not true, the whole "
            "'ErrorData names the object whose read failed' reading of "
            "R313 has to be re-argued from scratch",
        )

    def test_the_precedent_number_is_the_outer_envelopes_own_id(self):
        # Read from the frozen module, not retyped: the point is the
        # identity, and a hand-copied 0x6E9D would prove only that this
        # test can type.
        self.assertEqual(28317, legacy.GSCN_RUNTIME_PROTOCOL_RES)

    def test_the_capture_itself_carries_both_ids_in_reader_order(self):
        """Both numbers are literally in the bytes R313 sent, in the order
        the client's reader meets them: the envelope's id first, then the
        vital's.  Parsed out of the captured frame rather than asserted, so
        this cannot pass on a coincidence of two constants.
        """
        pc = bytes.fromhex(
            R313CaptureParityTests._R313_DOCK153_INITIAL_HEX.replace(" ", "")
        )
        # `make_runtime_vitals` writes, in order:
        #   [0]      0x12          [1:3]   outer id
        #   [3]      0x14          [4:8]   u32 0
        #   [8:10]   08 04         [10:12] 0B 02
        #   [12]     0x12          [13:15] record count
        #   [15]     0x12          [16:18] msg id
        #   [18]     0x0B          [19]    vital version
        #   [20:]    the record, then the trailing 0B 00 change mask
        self.assertEqual(pc[0], 0x12)
        outer_id = struct.unpack_from("<H", pc, 1)[0]
        self.assertEqual(outer_id, legacy.GSCN_RUNTIME_PROTOCOL_RES)
        self.assertEqual(struct.unpack_from("<H", pc, 13)[0], 1,
                         "the collection carries exactly one record")
        vital_id = struct.unpack_from("<H", pc, 16)[0]
        self.assertEqual(
            vital_id, survey.NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID)
        self.assertEqual(pc[18:20], bytes([0x0B, 0]),
                         "vital_version 0, as R313's console line reports")
        self.assertEqual(pc[20], 0x0B,
                         "and the record starts right after it")

    def test_read_failure_layer_names_the_layer_not_the_cause(self):
        self.assertEqual(
            "OUTER_ENVELOPE",
            survey.read_failure_layer(legacy, 28317))
        self.assertEqual(
            "THIS_VITAL",
            survey.read_failure_layer(legacy, 50351))
        # A number this module has no name for must NOT come back as one of
        # the two named layers -- an id it cannot place is some other
        # class's, and saying "outer envelope" there would send an attended
        # round after the wrong frame.
        self.assertEqual(
            "SOMETHING_ELSE",
            survey.read_failure_layer(legacy, 0x1FB2))

    def test_the_dialog_number_itself_is_a_transcription_not_a_recompute(self):
        """The honest limit of the test above (pf-adversary D11).

        50351 reaches this repository as text in R313's letter, read off a
        screenshot the gate's forbidden-path guard can never let in.  If the
        observer or the letter mistyped it, the equality test still passes,
        because the transcription is being compared to the id it was
        recognised as.  What that test rules out is a DIFFERENT number being
        the class id; it cannot rule out a mistyped dialog.  Pinned here so
        the limit travels with the claim.
        """
        self.assertEqual(
            survey.R313_SURVEY_DIALOG_ERRORDATA, 50351,
            "the number as R313's letter transcribes it -- change this only "
            "with a new attended observation, never to make another test "
            "pass",
        )

    def test_the_composer_still_refuses_to_default_the_id(self):
        """Naming the id does not mean this module now picks it.  The
        constant exists so the number has its evidence attached; the
        caller still supplies it (`m2_survey_trial.py` is where the trial's
        two numbers live, and that file is chief's).
        """
        import inspect

        sig = inspect.signature(survey.encode_add_survey_data_outer)
        self.assertIs(sig.parameters["msg_id"].default, inspect.Parameter.empty)


if __name__ == "__main__":
    unittest.main()
