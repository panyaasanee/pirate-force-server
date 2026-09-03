"""LANE-A: the two click vitals, and what the missing rows cost today.

FOUR QUESTIONS DECIDE WHETHER THIS MODULE IS WORTH LANDING, and this file
is organised as those four:

  1. Do the two lengths hold at more than one layer?  The composition is
     checked against ``ON_LAND_VITAL`` 23 and ``TARGET_POS_VITAL`` 24
     (LANE-E's rows -- a sanity check on the tag widths, NOT a proof of
     this file's field list, and 24 is a number LANE-E's own docstring
     flags as single-sourced), and against the byte counts three committed
     capture reports state: 45, 29 and the 76-byte frame where ``0x1ADD``
     sits mid-frame and so pins 11 on its own.
  2. Is it fail-closed where it says it is?  An id with no declared length,
     a lying envelope, one byte too many, a truncated body, a decoder that
     raises: each refuses by a REGISTERED name and hands back nothing.
  3. Does it read what main cannot?  A frame whose click is not first is
     driven through the module, and the identities come back in wire order.
  4. What does the missing row cost on the REAL dispatcher?  A logged-in
     session, the click frame shape ``v141``'s own builder writes
     (``v141:6300-6315``), and the position in it measured being thrown
     away.  Question 4 is the one a described paragraph cannot answer, and
     it is why this file boots ``make_state_class`` instead of asserting on
     source text.

THE MEASUREMENT THESE TESTS PIN IS TODAY'S DEFECT, NOT A FIX.  Nothing in
this repository calls ``world_click_vitals`` yet (a property two independent
detectors enforce -- a text scan and an AST scan that reads call arguments,
after pf-adversary proved the first draft's import-only scan blind to
``importlib.import_module``), and
the two rows that would let every OTHER walk-based lane read a click frame
live in ``vital_walk._LENGTHS_BY_LEGACY_NAME``, which is LANE-E's file.
``CORE-REQUEST 20260903_1641`` is the ask; ``DispatchTodayTests`` below is
its evidence, and it is written so that it turns RED on the day the request
lands -- deliberately, so nobody has to remember to come back.
"""
from __future__ import annotations

import ast
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import vital_walk  # noqa: E402
from pirateforce_foundation import world_click_vitals as click  # noqa: E402
from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm import login_scene_override  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector,
    load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


# ---------------------------------------------------------------------------
# Frame builders.  Every body is composed from the frozen module's own tag
# helpers, in the field order v141's own builder writes -- never from a hand
# typed byte string, so a codec change turns this file red rather than
# leaving it agreeing with a fossil.
# ---------------------------------------------------------------------------


def _target_vital(legacy, actor_identity, kind=2, version=0):
    """``v141:6304-6307``: qword identity, then the u8 target kind."""
    body = legacy.qwordtag(0x32, actor_identity) + legacy.u8tag(0x08, kind)
    return (legacy.u16tag(0x12, legacy.TARGET_VITAL)
            + legacy.u8tag(0x0B, version) + body)


def _choose_npc(legacy, actor_identity, version=0):
    """``v141:6309-6312``: one qword actor identity and nothing else."""
    body = legacy.qwordtag(0x32, actor_identity)
    return (legacy.u16tag(0x12, legacy.CHOOSE_NPC)
            + legacy.u8tag(0x0B, version) + body)


def _target_pos_vital(legacy, x, y, z, heading=0.0, moving=1, tail=0):
    body = b"".join(legacy.f32tag(value) for value in (x, y, z, heading))
    body += legacy.u8tag(0x0B, moving) + legacy.u8tag(0x0B, tail)
    return (legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
            + legacy.u8tag(0x0B, 0) + body)


def _on_land_vital(legacy, x=1.0, y=2.0, z=3.0, heading=4.0, tail=1):
    body = b"".join(legacy.f32tag(value) for value in (x, y, z, heading))
    body += legacy.u16tag(0x0F, tail)
    return (legacy.u16tag(0x12, legacy.ON_LAND_VITAL)
            + legacy.u8tag(0x0B, 0) + body)


def _unknown_vital(legacy, vital_id=0x3BFB):
    """``CHOOSE_NPC_BY_TABLE_ID``: a click id nothing declares a length for."""
    return (legacy.u16tag(0x12, vital_id) + legacy.u8tag(0x0B, 0)
            + legacy.qwordtag(0x32, 1))


def _frame(legacy, vitals, *, vital_count=None, outer_mask=2, outer_id=None):
    if outer_id is None:
        outer_id = legacy.GSCN_RUNTIME_PROTOCOL_REQ
    if vital_count is None:
        vital_count = len(vitals)
    return bytes(
        legacy.u16tag(0x12, outer_id)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, outer_mask)
        + legacy.u16tag(0x12, vital_count)
        + b"".join(vitals)
    )


def _every_refusal_shape(legacy):
    """One parse object per registered refusal name, built from real frames.

    Kept next to the test that consumes it rather than inside it: the list
    is the module's refusal vocabulary, and a name added there with no
    shape here fails ``test_every_registered_refusal_name_is_one_this_
    module_can_answer`` rather than sitting unreachable.
    """
    pc = _frame(legacy, [
        _on_land_vital(legacy), _choose_npc(legacy, 0x2002)])
    parsed = legacy.parse_outer(pc)

    def _with(**fields):
        values = dict(
            outer_id=parsed.outer_id,
            outer_version=parsed.outer_version,
            outer_mask=parsed.outer_mask,
            vital_count=parsed.vital_count,
            nested_id=parsed.nested_id,
            nested_version=parsed.nested_version,
            nested_payload=parsed.nested_payload,
            nested_offset=parsed.nested_offset,
            raw_pc=parsed.raw_pc,
        )
        values.update(fields)
        return legacy.ParsedOuter(**values)

    class _Explodes:
        outer_id = legacy.GSCN_RUNTIME_PROTOCOL_REQ
        outer_mask = 2
        vital_count = 1
        nested_id = legacy.ON_LAND_VITAL
        nested_version = 0
        nested_offset = 15
        raw_pc = b"x" * 40

        @property
        def nested_payload(self):
            raise RuntimeError("boom")

    return (
        _Explodes(),
        _with(raw_pc="not bytes at all"),
        _with(vital_count=0),
        _with(vital_count=vital_walk.MAX_VITALS_PER_FRAME + 1),
        _with(nested_offset=None),
        _with(nested_payload=b""),
        legacy.parse_outer(_frame(legacy, [
            _on_land_vital(legacy), _choose_npc(legacy, 0x2002)],
            outer_id=0x1234)),
        legacy.parse_outer(_frame(legacy, [
            _on_land_vital(legacy), _choose_npc(legacy, 0x2002)],
            outer_mask=0)),
        legacy.parse_outer(_frame(legacy, [
            _on_land_vital(legacy), _unknown_vital(legacy)])),
        legacy.parse_outer(_frame(legacy, [
            _on_land_vital(legacy), _choose_npc(legacy, 0x2002)])[:-1]),
        legacy.parse_outer(_frame(legacy, [
            _on_land_vital(legacy), _choose_npc(legacy, 0x2002)]) + b"\x00"),
    )


class TheLengthsAreDerivedTests(unittest.TestCase):
    """Question 1: derived, and the derivation is checked against others'."""

    def setUp(self):
        self.legacy = _legacy()

    def test_the_method_reproduces_the_two_rows_lane_e_already_declares(self):
        """THE CONTROL, and the only reason to trust 11 and 9 from here.

        Composing ``ON_LAND_VITAL``'s and ``TARGET_POS_VITAL``'s bodies the
        same way this module composes the click bodies has to reproduce the
        numbers ``vital_walk`` already carries -- 23 and 24, derived by
        LANE-E from the R303 capture rather than from this lane's reasoning.
        A method that cannot reproduce a row somebody else measured has no
        business declaring one nobody has.
        """
        legacy = self.legacy
        declared = vital_walk.body_length_table(legacy)
        on_land = len(_on_land_vital(legacy)) - 5
        target_pos = len(_target_pos_vital(legacy, 1.0, 2.0, 3.0)) - 5
        self.assertEqual(on_land, declared[legacy.ON_LAND_VITAL])
        self.assertEqual(target_pos, declared[legacy.TARGET_POS_VITAL])
        self.assertEqual((on_land, target_pos), (23, 24))

    def test_the_two_click_lengths_are_what_the_frozen_builder_writes(self):
        """Not typed: measured off v141's own composed vital, minus header."""
        legacy = self.legacy
        lengths = click.body_lengths(legacy)
        self.assertEqual(
            lengths[legacy.TARGET_VITAL],
            len(_target_vital(legacy, 0x2002)) - 5)
        self.assertEqual(
            lengths[legacy.CHOOSE_NPC],
            len(_choose_npc(legacy, 0x2002)) - 5)
        self.assertEqual(
            (lengths[legacy.TARGET_VITAL], lengths[legacy.CHOOSE_NPC]),
            (11, 9))

    def test_the_committed_capture_lengths_close_on_these_rows(self):
        """The second layer, and it is a capture rather than a table.

        ``reports/PF_RE_V140_P86_Synthetic_Harness_Interaction_Pass_
        20260815.md`` states 45 bytes of protocol content for an inbound
        ``TargetVital`` + ``ChooseNPC`` pair from a live attended session,
        and ``docs/EXPERIMENT_LEDGER.md``'s SCENE-004 row states 29 bytes
        for a lone ``ChooseNPC``.  Both close exactly on 11 and 9 -- and
        neither is offered as proof of the serializer table, nor the table
        as proof of them (G-OBS: two layers, consistent, never one standing
        in for the other).
        """
        legacy = self.legacy
        pair = _frame(legacy, [
            _target_vital(legacy, 0x2057),
            _choose_npc(legacy, 0x2057),
        ])
        lone = _frame(legacy, [_choose_npc(legacy, 0x2057)])
        self.assertEqual(len(pair), 45)
        self.assertEqual(len(lone), 29)

    def test_the_composed_length_does_not_depend_on_the_value_in_it(self):
        """A row is a LENGTH, so it may not move with the identity in it.

        ``qwordtag``/``u8tag`` are fixed-width today, and composing with a
        single sentinel value would not notice a codec that stopped being
        (varint, a shorter form for a small number).  Composing the same
        body across the range the wire can carry does.
        """
        legacy = self.legacy
        widths = {
            len(_choose_npc(legacy, identity))
            for identity in (0, 1, 0x2002, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF)
        }
        self.assertEqual(widths, {14})
        kinds = {
            len(_target_vital(legacy, 0x2002, kind=kind))
            for kind in (0, 2, 255)
        }
        self.assertEqual(kinds, {16})

    def test_an_isolated_vital_keeps_v141s_own_invariant(self):
        """The output shape is pinned, not only the input shape.

        ``nested_payload == raw_pc[nested_offset + 5:]`` is what every
        decoder in this repository may assume of a ``ParsedOuter``
        (``vital_walk._isolated`` documents the same equation).  A mutant
        that set ``nested_offset`` to 5 on the isolated copy survived the
        first draft of this file.
        """
        legacy = self.legacy
        parsed = legacy.parse_outer(_frame(legacy, [
            _on_land_vital(legacy),
            _target_vital(legacy, 0x2002),
            _choose_npc(legacy, 0x2002, version=3),
        ]))
        walked = click._walk_with_click_lengths(legacy, parsed)
        self.assertTrue(walked.walked)
        for vital in walked.vitals:
            with self.subTest(vital=hex(vital.nested_id)):
                self.assertEqual(vital.vital_count, 1)
                self.assertEqual(vital.nested_offset, 0)
                self.assertEqual(
                    bytes(vital.nested_payload),
                    bytes(vital.raw_pc)[vital.nested_offset + 5:])
                self.assertEqual(vital.outer_id, parsed.outer_id)
        self.assertEqual(walked.vitals[-1].nested_version, 3)

    def test_the_capture_that_pins_eleven_on_its_own_closes_and_refuses(self):
        """``reports/PF_RE_V138_MARKER1_*_20260815.md:12``, both halves.

        45 alone constrains only ``a + b == 20``; it takes 29 as well to
        split it.  The frame that pins 11 BY ITSELF is the 76-byte V138
        one, where ``0x1ADD`` sits mid-frame so its end is measured against
        the NEXT vital's header: 15 + (5+11) + (5+11) + (5+24) = 76, zero
        leftover.  The middle vital is ``TeleportVital`` 0x25A2, whose
        length this lane does not declare -- so the same frame is also the
        cleanest proof the walk stays fail-closed on an id it has no row
        for, rather than guessing the boundary it could have inferred here.
        """
        legacy = self.legacy
        teleport = (legacy.u16tag(0x12, 0x25A2) + legacy.u8tag(0x0B, 4)
                    + legacy.u8tag(0x0B, 2) + legacy.u16tag(0x0B, 0)
                    + legacy.u16tag(0x0B, 0) + legacy.u16tag(0x0F, 0))
        self.assertEqual(len(teleport) - 5, 11)
        pc = _frame(legacy, [
            _target_vital(legacy, 0x203D),
            teleport,
            _target_pos_vital(legacy, 1.0, 2.0, 3.0),
        ])
        self.assertEqual(len(pc), 76)
        self.assertEqual(
            click.read_click(legacy, legacy.parse_outer(pc)).reason,
            "leading_click_is_mains_branch")
        shifted = _frame(legacy, [
            _on_land_vital(legacy),
            _target_vital(legacy, 0x203D),
            teleport,
        ])
        self.assertEqual(
            click.read_click(legacy, legacy.parse_outer(shifted)).reason,
            "unknown_vital_id")

    def test_the_ids_are_read_by_name_and_a_partial_module_declares_none(self):
        """A frozen-snapshot rename must empty the table, never guess."""
        legacy = self.legacy
        empty = click.body_lengths(mock.Mock(spec=[]))
        self.assertEqual(empty, {})
        self.assertEqual(
            sorted(click.body_lengths(legacy)),
            sorted((legacy.TARGET_VITAL, legacy.CHOOSE_NPC)))

    def test_the_merged_table_adds_the_click_rows_and_changes_no_other(self):
        """Written to survive the landing, not to punish it.

        A draft asserted the merged table adds EXACTLY two ids, which would
        go red the day ``vital_walk`` declares them itself -- the state the
        module docstring promises is still correct.  pf-adversary caught the
        contradiction.  What must hold on both sides of that landing is:
        every borrowed row survives untouched, and both click rows are
        present with this module's lengths.
        """
        legacy = self.legacy
        borrowed = vital_walk.body_length_table(legacy)
        merged = click.declared_lengths_for_the_walk(legacy)
        for vital_id, length in borrowed.items():
            self.assertEqual(merged[vital_id], length)
        for vital_id, length in click.body_lengths(legacy).items():
            self.assertEqual(merged[vital_id], length)
        self.assertLessEqual(set(borrowed), set(merged))


class ItReadsWhatMainCannotTests(unittest.TestCase):
    """Question 3: the click that is not first, recovered in wire order."""

    def setUp(self):
        self.legacy = _legacy()

    def _read(self, vitals, **kwargs):
        parsed = self.legacy.parse_outer(
            _frame(self.legacy, vitals, **kwargs))
        return click.read_click(self.legacy, parsed)

    def test_a_click_behind_a_position_is_read(self):
        legacy = self.legacy
        read = self._read([
            _target_pos_vital(legacy, 1.0, 2.0, 3.0),
            _target_vital(legacy, 0x2002),
            _choose_npc(legacy, 0x2002),
        ])
        self.assertEqual(read.identities, (0x2002,))
        self.assertEqual(read.reason, "read")

    def test_several_identities_come_back_in_wire_order(self):
        legacy = self.legacy
        read = self._read([
            _on_land_vital(legacy),
            _choose_npc(legacy, 0x2002),
            _choose_npc(legacy, 0x2003),
        ])
        self.assertEqual(read.identities, (0x2002, 0x2003))

    def test_a_leading_click_is_left_to_main(self):
        """No second author for a frame the frozen path already reads."""
        legacy = self.legacy
        read = self._read([
            _target_vital(legacy, 0x2002),
            _choose_npc(legacy, 0x2002),
            _target_pos_vital(legacy, 1.0, 2.0, 3.0),
        ])
        self.assertEqual(read.identities, ())
        self.assertEqual(read.reason, "leading_click_is_mains_branch")
        self.assertTrue(click.leading_click_is_mains_branch(
            legacy, legacy.parse_outer(_frame(legacy, [
                _choose_npc(legacy, 0x2002)]))))

    def test_a_frame_with_no_click_in_it_is_named_not_refused(self):
        legacy = self.legacy
        read = self._read([
            _target_pos_vital(legacy, 1.0, 2.0, 3.0),
            _on_land_vital(legacy),
        ])
        self.assertEqual(read.identities, ())
        self.assertEqual(read.reason, "no_click_vital_in_this_frame")

    def test_the_identity_is_the_one_the_frozen_parser_reads(self):
        """Read through ``parse_choose_npc``, not by unpacking bytes here."""
        legacy = self.legacy
        for identity in (0x2002, 0x7FFFFFFFFFFFFFFF, 1):
            with self.subTest(identity=identity):
                read = self._read([
                    _on_land_vital(legacy),
                    _choose_npc(legacy, identity),
                ])
                self.assertEqual(read.identities, (identity,))

    def test_every_reason_it_can_answer_with_is_registered(self):
        legacy = self.legacy
        seen = {
            self._read([_on_land_vital(legacy),
                        _choose_npc(legacy, 0x2002)]).reason,
            self._read([_on_land_vital(legacy)]).reason,
            self._read([_target_pos_vital(legacy, 1.0, 2.0, 3.0),
                        _unknown_vital(legacy)]).reason,
            self._read([_choose_npc(legacy, 0x2002)]).reason,
            click.read_click(mock.Mock(spec=[]), object()).reason,
        }
        self.assertEqual(seen - set(click.READ_NAMES), set())
        self.assertEqual(len(seen), 5)


class ItIsFailClosedTests(unittest.TestCase):
    """Question 2: every refusal by name, nothing handed back."""

    def setUp(self):
        self.legacy = _legacy()

    def _read(self, pc):
        return click.read_click(self.legacy, self.legacy.parse_outer(pc))

    def test_an_id_with_no_declared_length_refuses_the_whole_frame(self):
        """``CHOOSE_NPC_BY_TABLE_ID`` 0x3BFB has no parser and no length.

        The identity in the vital BEFORE it is deliberately not returned:
        a table that disagrees with the frame somewhere in the middle makes
        every vital in it untrustworthy, including the ones that looked
        right (``vital_walk._walk_fields``' own rule, kept here).
        """
        legacy = self.legacy
        read = self._read(_frame(legacy, [
            _on_land_vital(legacy),
            _choose_npc(legacy, 0x2002),
            _unknown_vital(legacy),
        ]))
        self.assertEqual(read.identities, ())
        self.assertEqual(read.reason, "unknown_vital_id")

    def test_a_lying_vital_count_refuses(self):
        legacy = self.legacy
        read = self._read(_frame(
            legacy,
            [_on_land_vital(legacy), _choose_npc(legacy, 0x2002)],
            vital_count=3))
        self.assertEqual(read.reason, "truncated_vital")

    def test_one_byte_too_many_refuses(self):
        legacy = self.legacy
        read = self._read(_frame(legacy, [
            _on_land_vital(legacy), _choose_npc(legacy, 0x2002)]) + b"\x00")
        self.assertEqual(read.reason, "trailing_bytes_after_last_vital")

    def test_a_truncated_body_refuses(self):
        legacy = self.legacy
        read = self._read(_frame(legacy, [
            _on_land_vital(legacy), _choose_npc(legacy, 0x2002)])[:-1])
        self.assertEqual(read.reason, "truncated_vital")

    def test_a_frame_that_is_not_a_vital_collection_refuses(self):
        legacy = self.legacy
        for kwargs, expected in (
            ({"outer_mask": 0}, "not_a_vital_collection"),
            ({"outer_id": 0x1234}, "not_a_runtime_protocol_req"),
        ):
            with self.subTest(**kwargs):
                read = self._read(_frame(legacy, [
                    _on_land_vital(legacy),
                    _choose_npc(legacy, 0x2002)], **kwargs))
                self.assertEqual(read.reason, expected)

    def test_a_parse_object_that_lies_about_its_own_offset_refuses(self):
        """The object is refused -- and NOT by the line that looks like it.

        ``nested_payload == raw_pc[nested_offset + 5:]`` holds on every frame
        ``parse_outer`` built, and the module checks it.  A mutant run this
        round (recorded in the module's own comment) DELETED that check and
        this test stayed green: with fixed declared lengths and a walk that
        must land exactly on the last byte, a lying offset is refused by the
        geometry.  So this test pins the OUTCOME -- such an object never
        yields identities -- and deliberately does not claim which line
        produces it.
        """
        legacy = self.legacy
        pc = _frame(legacy, [
            _on_land_vital(legacy), _choose_npc(legacy, 0x2002)])
        parsed = legacy.parse_outer(pc)
        lied = legacy.ParsedOuter(
            outer_id=parsed.outer_id,
            outer_version=parsed.outer_version,
            outer_mask=parsed.outer_mask,
            vital_count=parsed.vital_count,
            nested_id=parsed.nested_id,
            nested_version=parsed.nested_version,
            nested_payload=parsed.nested_payload,
            nested_offset=parsed.nested_offset + 1,
            raw_pc=parsed.raw_pc,
        )
        read = click.read_click(legacy, lied)
        self.assertEqual(
            read, click.ClickRead((), "envelope_payload_disagrees"))

    def test_a_decoder_that_raises_drops_that_vital_and_keeps_the_rest(self):
        legacy = self.legacy
        pc = _frame(legacy, [
            _on_land_vital(legacy),
            _choose_npc(legacy, 0x2002),
            _choose_npc(legacy, 0x2003),
        ])
        parsed = legacy.parse_outer(pc)
        real = legacy.parse_choose_npc
        calls = []

        def _explodes_once(vital):
            calls.append(vital)
            if len(calls) == 1:
                raise ValueError("boom")
            return real(vital)

        with mock.patch.object(legacy, "parse_choose_npc", _explodes_once):
            read = click.read_click(legacy, parsed)
        self.assertEqual(read.identities, (0x2003,))

    def test_a_decoder_that_answers_with_the_wrong_type_is_dropped(self):
        legacy = self.legacy
        parsed = legacy.parse_outer(_frame(legacy, [
            _on_land_vital(legacy), _choose_npc(legacy, 0x2002)]))
        with mock.patch.object(legacy, "parse_choose_npc",
                               lambda vital: "0x2002"):
            read = click.read_click(legacy, parsed)
        self.assertEqual(read, click.ClickRead(
            (), "no_click_vital_in_this_frame"))

    def test_an_honest_offset_with_a_replaced_payload_is_refused(self):
        """THE INPUT THAT SEPARATES THE INVARIANT CHECK FROM THE GEOMETRY.

        pf-adversary found it: with the offset honest and the payload
        replaced, deleting the invariant check makes the walk RETURN AN
        IDENTITY (measured: ``ClickRead((8194,), "read")``).  So a mutant
        that removes it is now caught here, and the earlier note that no
        test could tell the two apart is superseded.
        """
        legacy = self.legacy
        pc = _frame(legacy, [
            _on_land_vital(legacy), _choose_npc(legacy, 0x2002)])
        parsed = legacy.parse_outer(pc)
        replaced = legacy.ParsedOuter(
            outer_id=parsed.outer_id,
            outer_version=parsed.outer_version,
            outer_mask=parsed.outer_mask,
            vital_count=parsed.vital_count,
            nested_id=parsed.nested_id,
            nested_version=parsed.nested_version,
            nested_payload=b"",
            nested_offset=parsed.nested_offset,
            raw_pc=parsed.raw_pc,
        )
        self.assertEqual(
            click.read_click(legacy, replaced),
            click.ClickRead((), "envelope_payload_disagrees"))

    def test_the_envelope_bounds_each_refuse_by_their_own_name(self):
        """Five branches no test reached in the first draft.

        pf-adversary traced line coverage and found the type and bound
        checks never executed, with five surviving mutants to prove it
        (drop the vital cap, widen the count to zero, accept a half-loaded
        legacy module, delete the mask check, move a bound by one).
        """
        legacy = self.legacy
        pc = _frame(legacy, [
            _on_land_vital(legacy), _choose_npc(legacy, 0x2002)])
        parsed = legacy.parse_outer(pc)

        def _with(**fields):
            values = dict(
                outer_id=parsed.outer_id,
                outer_version=parsed.outer_version,
                outer_mask=parsed.outer_mask,
                vital_count=parsed.vital_count,
                nested_id=parsed.nested_id,
                nested_version=parsed.nested_version,
                nested_payload=parsed.nested_payload,
                nested_offset=parsed.nested_offset,
                raw_pc=parsed.raw_pc,
            )
            values.update(fields)
            return legacy.ParsedOuter(**values)

        cases = (
            (_with(raw_pc="not bytes at all"), "raw_pc_not_bytes"),
            (_with(vital_count=0), "vital_count_not_positive"),
            (_with(vital_count=-1), "vital_count_not_positive"),
            (_with(vital_count=None), "vital_count_not_positive"),
            (_with(vital_count=vital_walk.MAX_VITALS_PER_FRAME + 1),
             "vital_count_too_large"),
            (_with(nested_offset=None), "nested_offset_not_a_position"),
            (_with(nested_offset=-1), "nested_offset_not_a_position"),
            (_with(nested_offset=len(pc) + 1), "nested_offset_not_a_position"),
        )
        for lied, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(click.read_click(legacy, lied).reason,
                                 expected)

    def test_a_legacy_module_that_declares_one_click_id_is_refused(self):
        """Half a vocabulary is not a vocabulary.

        A mutant that relaxed the check to "at least one id" survived the
        first draft: with only ``CHOOSE_NPC`` known, a ``TargetVital`` in
        the frame has no declared length, and the module would have been
        reading frames it cannot walk closed.
        """
        legacy = self.legacy
        half = mock.Mock(spec=["CHOOSE_NPC"])
        half.CHOOSE_NPC = legacy.CHOOSE_NPC
        parsed = legacy.parse_outer(_frame(legacy, [
            _on_land_vital(legacy), _choose_npc(legacy, 0x2002)]))
        self.assertEqual(
            click.read_click(half, parsed),
            click.ClickRead((), "legacy_module_missing_click_ids"))

    def test_a_parse_object_whose_field_explodes_is_refused_by_name(self):
        legacy = self.legacy

        class _Explodes:
            outer_id = legacy.GSCN_RUNTIME_PROTOCOL_REQ
            outer_mask = 2
            vital_count = 1
            nested_id = legacy.ON_LAND_VITAL
            nested_version = 0
            nested_offset = 15

            @property
            def raw_pc(self):
                return b"x" * 40

            @property
            def nested_payload(self):
                raise RuntimeError("boom")

        self.assertEqual(
            click.read_click(legacy, _Explodes()),
            click.ClickRead((), "parse_object_refused_to_answer"))

    def test_every_registered_refusal_name_is_one_this_module_can_answer(self):
        """The registry is not decoration: each name has a reachable input.

        A mutant that added a sixth, never-produced name to ``READ_NAMES``
        survived the first draft, so the pin is now "every name is
        reachable" rather than a count.
        """
        legacy = self.legacy
        reached = set()
        for parsed in _every_refusal_shape(legacy):
            reached.add(click.read_click(legacy, parsed).reason)
        reached.add(click.read_click(mock.Mock(spec=[]), object()).reason)
        # The three names a WALKED frame can still answer with.
        reached.add(click.read_click(legacy, legacy.parse_outer(_frame(
            legacy, [_on_land_vital(legacy)]))).reason)
        reached.add(click.read_click(legacy, legacy.parse_outer(_frame(
            legacy, [_choose_npc(legacy, 0x2002)]))).reason)
        reached.add(click.read_click(legacy, legacy.parse_outer(_frame(
            legacy, [_on_land_vital(legacy),
                     _choose_npc(legacy, 0x2002)]))).reason)
        self.assertEqual(set(click.READ_NAMES) - reached, set())

    def test_nothing_it_can_be_handed_makes_it_raise(self):
        legacy = self.legacy
        for payload in (None, object(), 0, "", b"", [],
                        mock.Mock(spec=[])):
            with self.subTest(payload=repr(payload)[:24]):
                self.assertEqual(
                    click.read_click(legacy, payload).identities, ())
                self.assertFalse(
                    click.leading_click_is_mains_branch(legacy, payload))

    def test_the_console_lines_are_ascii_and_carry_the_count(self):
        line = click.rescued_console_line((0x2002, 0x2003), 5)
        refused = click.refused_console_line("unknown_vital_id", 5)
        for text in (line, refused):
            with self.subTest(text=text):
                text.encode("ascii")
                self.assertIn("vital_count=5", text)
        self.assertIn("0x2002,0x2003", line)
        self.assertIn(click.CONSOLE_TOKEN, line)
        self.assertIn("reason=unknown_vital_id", refused)
        self.assertEqual(
            (click.CONSOLE_TOKEN, click.REFUSAL_TOKEN),
            ("LANE_A_CLICK_VITAL_RESCUED", "LANE_A_CLICK_VITAL_REFUSED"))
        self.assertIn("identities=none", click.rescued_console_line((), 1))


class DispatchTodayTests(unittest.TestCase):
    """Question 4: what the missing rows cost, on the real dispatcher.

    THESE TESTS PIN A DEFECT, NOT A FIX, and they are written to turn RED
    the day ``CORE-REQUEST 20260903_1641`` lands the two rows in
    ``vital_walk._LENGTHS_BY_LEGACY_NAME`` -- deliberately, so the round
    that lands them has to come back here and rewrite the assertions as the
    behaviour the request promised.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        pin = mock.patch.dict(gm_accounts.os.environ, {
            login_scene_override.ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_gm_login_scene.json"),
            login_scene_override.STANDALONE_ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_standalone_map.json"),
        })
        pin.start()
        self.addCleanup(pin.stop)
        self.legacy = _legacy()
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations")
        self.store.migrate()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(1, 0, self.legacy.V135_PLAYER_X,
                     self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        field_mobs.load_roster()

    def _started_session(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            state = state_type(token)
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_client_login_pc(token)))
            state.dispatch(self.legacy.parse_outer(
                self.legacy._V25_REAL_CREATE_PC))
            character = self.store.list_characters(
                state.foundation.account_id)[-1]
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)))
            state.dispatch(self.legacy.parse_outer(_frame(
                self.legacy,
                [_target_pos_vital(self.legacy, 100.0, 200.0, 300.0)])))
        return state

    def _dispatch(self, state, vitals):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            replies = state.dispatch(self.legacy.parse_outer(
                _frame(self.legacy, vitals)))
        return replies or [], out.getvalue() + err.getvalue()

    def _an_actor_in_this_scene(self, state):
        index = sorted(state.population_indices)[0]
        return 0x2000 + 1 + index

    def test_lane_e_still_declares_neither_click_id(self):
        """THE TRIPWIRE, and it lives with the rest of the tripwires.

        The premise of this whole class: while ``vital_walk`` declares no
        length for either click id, a frame carrying one cannot be walked
        by anybody.  The day ``CORE-REQUEST 20260903_1641`` lands, this
        goes red first and the two tests below go red with it -- which is
        the point.  A draft kept this in the "nothing calls this" class,
        where a red would have read as a wiring bug.
        """
        legacy = self.legacy
        declared = vital_walk.body_length_table(legacy)
        self.assertNotIn(legacy.TARGET_VITAL, declared)
        self.assertNotIn(legacy.CHOOSE_NPC, declared)

    def test_a_click_that_leads_the_frame_reaches_mains_branch_today(self):
        """The control: without it, "silence" below could be any cause.

        "REACHES", not "is answered": pf-adversary measured a leading click
        naming an unarmed identity getting zero replies, and the reply
        count on an armed one falling 3, 2, 2 across repeat clicks.  This
        asserts the difference the round claims -- a first click on an
        armed identity replies, the same click behind a position does not
        -- and asserts no number.
        """
        state = self._started_session("click_leads")
        identity = self._an_actor_in_this_scene(state)
        replies, _console = self._dispatch(state, [
            _target_vital(self.legacy, identity),
            _choose_npc(self.legacy, identity),
        ])
        self.assertTrue(replies)

    def test_a_click_behind_a_position_is_answered_by_nobody_today(self):
        """MEASURED SILENCE, and the module reads the same frame.

        ``runtime.py``'s guard and ``v141:4396`` both test
        ``parsed.nested_id``, which ``parse_outer`` fills from the FIRST
        vital only, so this frame reaches neither the lane's responders nor
        the frozen loop.  The second half of this test is the value of the
        request: the identity is in the frame and readable.
        """
        state = self._started_session("click_behind")
        identity = self._an_actor_in_this_scene(state)
        vitals = [
            _target_pos_vital(self.legacy, 1.0, 2.0, 3.0),
            _target_vital(self.legacy, identity),
            _choose_npc(self.legacy, identity),
        ]
        replies, _console = self._dispatch(state, vitals)
        self.assertEqual(replies, [])
        read = click.read_click(
            self.legacy,
            self.legacy.parse_outer(_frame(self.legacy, vitals)))
        self.assertEqual(read.identities, (identity,))

    def test_the_position_in_a_click_frame_is_thrown_away_today(self):
        """THE COST, on the frame shape v141's own builder writes.

        ``v141:6300-6315`` composes ``TargetVital`` + ``ChooseNPC`` + a
        TRAILING ``TargetPosVital``.  The click is answered (it leads), and
        the position in the same frame reaches nobody: the frozen parser
        reads only the first vital's body, and ``vital_walk``'s promotion --
        which exists to rescue exactly this -- refuses the frame because the
        two click ids have no declared length.  That is the R303 freeze
        (a player 173 units from a drop refused as 9250 away) on the frame
        shape a click produces.

        With the two rows added the same frame promotes the position and
        still answers the click; that measurement is in the round file and
        in the CORE-REQUEST, made by patching LANE-E's table, which is why
        it is NOT asserted here: a patched table is a mock, and this class
        only states what main does today.
        """
        state = self._started_session("click_frame_position")
        identity = self._an_actor_in_this_scene(state)
        before = state.last_target_pos
        self.assertIsNotNone(before)
        replies, console = self._dispatch(state, [
            _target_vital(self.legacy, identity),
            _choose_npc(self.legacy, identity),
            _target_pos_vital(self.legacy, 21482.5, 9433.3, 498.0),
        ])
        self.assertTrue(replies)
        self.assertEqual(state.last_target_pos, before)
        self.assertIn("%s reason=unknown_vital_id"
                      % (vital_walk.VITAL_WALK_REFUSED_TOKEN,), console)

    def test_the_refusal_is_the_missing_rows_and_not_something_else(self):
        """Same frame, two rows added: the walk closes and names the click.

        Driven on the module's own merged table rather than on the
        dispatcher, so nothing here depends on patching LANE-E's module.
        """
        state = self._started_session("click_frame_rows")
        identity = self._an_actor_in_this_scene(state)
        pc = _frame(self.legacy, [
            _target_vital(self.legacy, identity),
            _choose_npc(self.legacy, identity),
            _target_pos_vital(self.legacy, 21482.5, 9433.3, 498.0),
        ])
        parsed = self.legacy.parse_outer(pc)
        self.assertFalse(
            vital_walk.walk_nested_vitals(self.legacy, parsed).walked)
        walked = click._walk_with_click_lengths(self.legacy, parsed)
        self.assertTrue(walked.walked)
        self.assertEqual(
            [vital.nested_id for vital in walked.vitals],
            [self.legacy.TARGET_VITAL, self.legacy.CHOOSE_NPC,
             self.legacy.TARGET_POS_VITAL])
        x, y, z = self.legacy.parse_target_pos_vital(walked.vitals[-1])[:3]
        self.assertAlmostEqual(x, 21482.5, places=1)
        self.assertAlmostEqual(y, 9433.3, places=1)
        self.assertAlmostEqual(z, 498.0, places=1)
        self.assertEqual(
            click.read_click(self.legacy, parsed).reason,
            "leading_click_is_mains_branch")


class NothingCallsThisYetTests(unittest.TestCase):
    """The husk is DECLARED, so wiring it later is a reviewed change.

    THE FIRST DRAFT OF THIS CLASS HAD THE HOLE THIS REPOSITORY DOCUMENTED
    TEN HOURS EARLIER.  It walked only ``ast.Import``/``ast.ImportFrom``, so
    an edge written as ``importlib.import_module("...")`` or ``__import__``
    was invisible -- and pf-adversary proved it live by adding such an edge
    to ``lane_hooks/lane_a_choose_npc_scene2.py``, a module ``lane_hooks``
    imports on every boot, with this class still green.  LANE-B's aggro
    lane records the same hole being closed the day before (round
    ``1tz15e``, pirate-force-server ``#658``; its module is deliberately
    not named here -- that lane pins an exact list of the files mentioning
    it, and this file must not join it).  Two independent detectors now
    run: a text scan over four trees, and an AST scan that reads call
    arguments as well as import statements.
    """

    def test_no_file_in_the_repository_names_this_module(self):
        """The text scan: crude on purpose, and it sees every spelling.

        A string built by concatenation defeats it, which is why the AST
        scan below reads calls too; between them, an edge has to be written
        deliberately obscurely to hide, and that is a reviewable act rather
        than an oversight.
        """
        roots = (
            ROOT / "src",
            ROOT / "tools",
            ROOT / "scenarios",
            ROOT / "migrations",
        )
        mine = {
            (ROOT / "src" / "pirateforce_foundation"
             / "world_click_vitals.py").resolve(),
            Path(__file__).resolve(),
        }
        offenders = []
        for root in roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.resolve() in mine:
                    continue
                if path.suffix not in {".py", ".json", ".sql"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if "world_click_vitals" in text:
                    offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(offenders, [])

    def test_no_module_in_the_package_imports_this_one_by_ast(self):
        package = ROOT / "src" / "pirateforce_foundation"
        offenders = []
        for path in sorted(package.rglob("*.py")):
            if path.name == "world_click_vitals.py":
                continue
            if _ast_mentions(ast.parse(path.read_text(encoding="utf-8"))):
                offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(offenders, [])

    def test_the_ast_helper_sees_every_import_shape_including_the_hidden(self):
        """Prove the detector bites before relying on it.

        The last three are the shapes the first draft let through, the same
        three LANE-B's aggro lane had to close a day earlier.
        """
        for snippet in (
            "from . import world_click_vitals",
            "from .world_click_vitals import read_click",
            "import pirateforce_foundation.world_click_vitals as w",
            "from pirateforce_foundation import world_click_vitals",
            "import importlib\n"
            "w = importlib.import_module('"
            "pirateforce_foundation.world_click_vitals')",
            "w = __import__('pirateforce_foundation.world_click_vitals')",
            "w = getattr(mod, 'world_click_vitals')",
        ):
            with self.subTest(snippet=snippet.splitlines()[-1][:40]):
                self.assertTrue(_ast_mentions(ast.parse(snippet)))
        self.assertFalse(_ast_mentions(ast.parse("from . import store")))
        self.assertFalse(_ast_mentions(ast.parse("w = 'world click vitals'")))


def _ast_mentions(tree) -> bool:
    """True when the parsed module names this one in an import OR a call.

    Import nodes are the easy half.  The half that matters is
    ``ast.Constant``: ``importlib.import_module(...)``, ``__import__(...)``
    and ``getattr(module, "...")`` all carry the name as a plain string
    argument, and a scan that reads only import statements calls a live
    edge clean -- measured in this repository twice, once by
    pf-adversary on this very file.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""] + [
                alias.name for alias in node.names]
        elif isinstance(node, ast.Call):
            names = [
                argument.value for argument in node.args
                if isinstance(argument, ast.Constant)
                and isinstance(argument.value, str)
            ]
        else:
            continue
        if any("world_click_vitals" in name for name in names):
            return True
    return False


if __name__ == "__main__":
    unittest.main()
