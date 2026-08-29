"""LANE-B: the console's census count must come from bytes the client gets.

ROUND z096sw.  ``mob_census_wire_count`` exists to turn a console field
that was an INPUT into one that is a MEASUREMENT, so the tests that matter
here are the ones that break the measurement rather than the ones that
confirm it on a healthy frame:

  * a ``pc`` and a ``frame`` that are DIFFERENT collections must produce a
    named absence, not the pc's count.  That is the regression pf-adversary
    built against ``test_world_wipe_headless_proof``'s first draft (update
    the pc, leave the frame stale, every reading stays green while every
    kill puts one body on the wire), and it is the only reason this is a
    module with a pair check instead of an inline ``%d``.
  * NOTHING here may raise.  Every caller is inside ``runtime.py``'s
    hit/death dispatch and ``v141:7440`` has no ``except``, so an escape
    takes the player's connection with it.  The refusal cases are driven
    with hostile inputs -- ``None``, text, truncated bytes, a legacy seam
    that raises -- and each is required to come back as a printable line.

The healthy-frame reading is proved against a REAL composed census (the
same ``world_population`` build the runtime composes), not a hand-built
buffer: a hand-built buffer would prove this module agrees with the test's
own idea of a collection header, which is not the claim.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_census_wire_count  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_population_handoff  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class _RaisingLegacy:
    """A legacy seam that refuses to frame anything."""

    def frame_pc(self, pc):
        raise RuntimeError("this seam refuses")


class _WrongFrameLegacy:
    """A legacy seam whose frame is never the pc's own frame."""

    def frame_pc(self, pc):
        return b"not-this-pc's-frame"


class _UncomparableFrame:
    """Bytes-like enough to be returned, hostile enough to refuse ``==``."""

    def __eq__(self, other):
        raise RuntimeError("this object refuses to be compared")

    __hash__ = None


class _UncomparableFrameLegacy:
    """A seam whose frame_pc succeeds and whose result cannot be compared.

    The narrow hole the first draft of the module left open: ``frame_pc``
    was inside the ``try`` and the ``==`` after it was not, so a seam like
    this one raised straight out of ``runtime.py``'s dispatch -- which is
    the listener thread, which is the player's connection.
    """

    def frame_pc(self, pc):
        return _UncomparableFrame()


class WireActorCountTests(unittest.TestCase):
    def setUp(self):
        self.legacy = _legacy()
        anchor = (
            self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y,
            self.legacy.V135_PLAYER_Z,
        )
        self.generation = world_population.build_world_population(
            self.legacy, anchor, world_population.CENSUS_COUNT,
            scene_id=world_population.SCENE_ID,
        )
        self.pc = self.generation.pc
        self.frame = self.legacy.frame_pc(self.pc)

    # ----- the reading, on bytes the runtime really composes -------------

    def test_a_real_census_measures_to_its_own_collection_header(self):
        reading = mob_census_wire_count.wire_actor_count(
            self.legacy, self.pc, self.frame)
        self.assertTrue(reading["measured"])
        self.assertIsNone(reading["reason"])
        # Cross-checked against the SAME function the headless proof calls
        # ``_declared_count``, not against a number this file chose.
        self.assertEqual(
            reading["count"],
            world_population_handoff.wire_count_of(self.pc),
        )
        # And it is not vacuous: the census really does carry actors.
        self.assertGreater(reading["count"], 0)

    def test_the_line_carries_both_numbers_and_the_callers_own_token(self):
        line = mob_census_wire_count.describe_census_recompose(
            self.legacy, "MOB_COMBAT_BAR_CENSUS_RECOMPOSE",
            self.pc, self.frame,
            target_identity=0x201F, input_count=108,
        )
        self.assertEqual(
            line,
            "MOB_COMBAT_BAR_CENSUS_RECOMPOSE actor_count=108 "
            "wire_actors=%d target=0x201F"
            % world_population_handoff.wire_count_of(self.pc),
        )
        self.assertTrue(line.isascii())
        self.assertNotIn("\n", line)

    # ----- the pair check, which is the whole reason this module exists ---

    def test_a_frame_that_is_not_this_pcs_frame_is_refused_by_name(self):
        # THE REGRESSION.  A stale frame beside a fresh pc: the pc's header
        # is perfectly readable and would give a reassuring number for
        # bytes no client receives.
        reading = mob_census_wire_count.wire_actor_count(
            self.legacy, self.pc, b"a different collection entirely")
        self.assertFalse(reading["measured"])
        self.assertIsNone(reading["count"])
        self.assertEqual(
            reading["reason"],
            mob_census_wire_count.REASON_FRAME_IS_NOT_THIS_PC,
        )
        line = mob_census_wire_count.describe_census_recompose(
            self.legacy, "MOB_DEATH_FRAMES_CENSUS_RECOMPOSE",
            self.pc, b"a different collection entirely",
            target_identity=0x201F, input_count=108,
        )
        self.assertIn("wire_actors=unmeasured", line)
        self.assertIn("reason=frame_is_not_this_pc", line)
        # The number that WOULD have been printed must not appear anywhere
        # on the line: a reader greps this to decide whether the world
        # survived, and a refusal that still shows the count is worse than
        # no line at all.
        self.assertNotIn(
            "wire_actors=%d" % world_population_handoff.wire_count_of(self.pc),
            line,
        )

    def test_the_pair_check_is_not_vacuous(self):
        # Drive the same call through a seam whose frame_pc NEVER matches,
        # so a version of the module that skipped the comparison would be
        # caught here even if the real seam happened to agree.
        reading = mob_census_wire_count.wire_actor_count(
            _WrongFrameLegacy(), self.pc, self.frame)
        self.assertFalse(reading["measured"])
        self.assertEqual(
            reading["reason"],
            mob_census_wire_count.REASON_FRAME_IS_NOT_THIS_PC,
        )

    # ----- never raises, on any of the shapes a dispatch can hand it ------

    def test_every_hostile_input_comes_back_as_a_printable_line(self):
        cases = (
            (self.legacy, None, None, mob_census_wire_count.REASON_PC_NOT_BYTES),
            (self.legacy, "text", b"", mob_census_wire_count.REASON_PC_NOT_BYTES),
            (self.legacy, bytearray(self.pc), self.frame,
             mob_census_wire_count.REASON_PC_NOT_BYTES),
            (self.legacy, self.pc, None,
             mob_census_wire_count.REASON_FRAME_NOT_BYTES),
            (self.legacy, self.pc, "text",
             mob_census_wire_count.REASON_FRAME_NOT_BYTES),
            # Empty bytes paired with THEIR OWN frame: the pair check
            # passes (they really are the same collection) and the header
            # read is what refuses.  Paired with a bare ``b""`` frame it
            # would refuse one step earlier, which is also correct and is
            # why the pair is built here rather than assumed -- the order
            # of the two checks is part of the contract.
            (self.legacy, b"", self.legacy.frame_pc(b""),
             mob_census_wire_count.REASON_HEADER_UNREADABLE),
            (self.legacy, b"", b"",
             mob_census_wire_count.REASON_FRAME_IS_NOT_THIS_PC),
            (_UncomparableFrameLegacy(), self.pc, self.frame,
             mob_census_wire_count.REASON_LEGACY_REFUSED),
            (_RaisingLegacy(), self.pc, self.frame,
             mob_census_wire_count.REASON_LEGACY_REFUSED),
            (None, self.pc, self.frame,
             mob_census_wire_count.REASON_LEGACY_REFUSED),
        )
        for legacy, pc, frame, expected in cases:
            with self.subTest(reason=expected):
                reading = mob_census_wire_count.wire_actor_count(
                    legacy, pc, frame)
                self.assertFalse(reading["measured"])
                self.assertIsNone(reading["count"])
                self.assertEqual(reading["reason"], expected)
                self.assertIn(reading["reason"],
                              mob_census_wire_count.UNMEASURED_REASONS)
                line = mob_census_wire_count.describe_census_recompose(
                    legacy, "MOB_COMBAT_BAR_CENSUS_RECOMPOSE", pc, frame,
                    target_identity=0x201F, input_count=108,
                )
                self.assertTrue(line.isascii())
                self.assertIn("wire_actors=unmeasured", line)
                self.assertIn("reason=%s" % expected, line)

    def test_a_truncated_header_is_unreadable_not_a_small_count(self):
        # Bytes that ARE a real pc's prefix: long enough to look plausible,
        # short enough that the header cannot be read.  The failure this
        # pins is a truncation reported as ``wire_actors=0``, which reads
        # as "the world is empty" rather than "nobody could tell".
        truncated = self.pc[:4]
        reading = mob_census_wire_count.wire_actor_count(
            self.legacy, truncated, self.legacy.frame_pc(truncated))
        self.assertFalse(reading["measured"])
        self.assertEqual(
            reading["reason"],
            mob_census_wire_count.REASON_HEADER_UNREADABLE,
        )

    # ----- the fields around the number ----------------------------------

    def test_a_missing_input_count_or_target_is_named_not_zeroed(self):
        line = mob_census_wire_count.describe_census_recompose(
            self.legacy, "MOB_COMBAT_BAR_CENSUS_RECOMPOSE",
            self.pc, self.frame,
        )
        self.assertIn("actor_count=none", line)
        self.assertIn("target=none", line)
        # A caller with no input count is not a caller whose input count is
        # zero, and a console reader must be able to tell those apart.
        self.assertNotIn("actor_count=0 ", line)
        self.assertNotIn("target=0x0", line)

    def test_a_bool_is_not_an_int_here(self):
        # ``True`` is an ``int`` in Python and would print as 1; a boolean
        # arriving in either field means a caller passed a flag where a
        # count belongs, which is a named absence, not the number one.
        line = mob_census_wire_count.describe_census_recompose(
            self.legacy, "MOB_COMBAT_BAR_CENSUS_RECOMPOSE",
            self.pc, self.frame,
            target_identity=True, input_count=True,
        )
        self.assertIn("actor_count=none", line)
        self.assertIn("target=none", line)

    def test_a_nonascii_or_missing_token_cannot_break_the_cp874_console(self):
        # The Thai character is written as an escape rather than a literal
        # so this source file stays pure ASCII (house rule: the bridge
        # console is cp874 and reads these files).  It is the same
        # character a mis-pasted token would carry.
        for token in (None, "", 123, "MOB\u0e01_TOKEN\n"):
            with self.subTest(token=repr(token)):
                line = mob_census_wire_count.describe_census_recompose(
                    self.legacy, token, self.pc, self.frame,
                    target_identity=0x201F, input_count=108,
                )
                self.assertTrue(line.isascii())
                self.assertNotIn("\n", line)
                self.assertIn("wire_actors=", line)

    def test_the_module_is_flagless_production_code(self):
        self.assertTrue(mob_census_wire_count.production_allowed)
        self.assertFalse(mob_census_wire_count.test_only)


if __name__ == "__main__":
    unittest.main()
