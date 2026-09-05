"""``ground_empty_trial``: the attended arm for an emptied floor.

COO-DECISION 20260905_1247 item 3 (the arm) and item 4 (production behaviour
unchanged until a screen answers).  The most important assertions in this file
are the UNARMED ones: an ordinary boot must be byte-identical to main, and a
console line that only appears in the log is still a difference an attended
reader has to explain.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import ground_empty_trial, mob_loot  # noqa: E402


class ArmReadingTests(unittest.TestCase):
    def test_only_the_exact_string_1_arms_it(self):
        for raw in ("1", " 1 ", "1\n"):
            with self.subTest(raw=raw):
                self.assertTrue(ground_empty_trial.armed({
                    ground_empty_trial.GROUND_EMPTY_TRIAL_ENV: raw}))

    def test_everything_else_is_unarmed(self):
        for environ in (
            {},
            {ground_empty_trial.GROUND_EMPTY_TRIAL_ENV: ""},
            {ground_empty_trial.GROUND_EMPTY_TRIAL_ENV: "0"},
            {ground_empty_trial.GROUND_EMPTY_TRIAL_ENV: "true"},
            {ground_empty_trial.GROUND_EMPTY_TRIAL_ENV: "yes"},
            {ground_empty_trial.GROUND_EMPTY_TRIAL_ENV: "11"},
            {ground_empty_trial.GROUND_EMPTY_TRIAL_ENV: None},
            {ground_empty_trial.GROUND_EMPTY_TRIAL_ENV: 1},
        ):
            with self.subTest(environ=environ):
                self.assertFalse(ground_empty_trial.armed(environ))

    def test_a_mapping_that_raises_reads_as_unarmed_not_as_an_exception(self):
        class Hostile(dict):
            def get(self, *_args, **_kwargs):
                raise RuntimeError("environment read failed")
        self.assertFalse(ground_empty_trial.armed(Hostile()))


class ComposedBytesTests(unittest.TestCase):
    def setUp(self):
        self.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_the_empty_generation_is_the_pinned_envelope_and_a_zero_count(self):
        pc = ground_empty_trial.empty_generation_pc(self.v)
        self.assertEqual(len(pc), mob_loot.DROP_ENVELOPE_SIZE)
        self.assertEqual(
            pc[:mob_loot.DROP_ENVELOPE_CONSTANT_SIZE],
            mob_loot.DROP_ENVELOPE_CONSTANT_PIN)
        self.assertEqual(pc[mob_loot.DROP_ENVELOPE_CONSTANT_SIZE + 1:],
                         b"\x00\x00")

    def test_it_differs_from_a_one_element_generation_only_after_the_count(self):
        """The point of composing through the same tags, made assertable.

        Everything up to and including the count TAG is the envelope every
        generation this lane has put on a real client's wire carries.  If this
        ever stops holding, the trial is measuring a frame the client has
        never been shown and a negative result would mean nothing.
        """
        one = mob_loot.DROP_ENVELOPE_PIN
        empty = ground_empty_trial.empty_generation_pc(self.v)
        head = mob_loot.DROP_ENVELOPE_CONSTANT_SIZE + 1
        self.assertEqual(empty[:head], one[:head])
        self.assertNotEqual(empty[head:], one[head:])


class ProductionIsUnchangedTests(unittest.TestCase):
    def setUp(self):
        self.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_unarmed_composes_nothing_and_prints_nothing(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            frames, line = ground_empty_trial.frames_for_empty_floor(
                self.v, environ={})
        self.assertEqual(frames, ())
        self.assertIsNone(line)
        self.assertEqual(buf.getvalue(), "")

    def test_armed_returns_one_framed_generation_and_says_so(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            frames, line = ground_empty_trial.frames_for_empty_floor(
                self.v,
                environ={ground_empty_trial.GROUND_EMPTY_TRIAL_ENV: "1"})
        self.assertEqual(len(frames), 1)
        pc, frame = frames[0]
        self.assertEqual(frame, self.v.frame_pc(pc))
        self.assertEqual(line, "GROUND_EMPTY_TRIAL_SENT elements=0 bytes=%d"
                         % mob_loot.DROP_ENVELOPE_SIZE)
        self.assertEqual(buf.getvalue().strip(), line)
        self.assertTrue(line.isascii())

    def test_a_serializer_that_will_not_compose_costs_the_frame_not_the_loop(self):
        class Broken:
            GSCN_RUNTIME_PROTOCOL_RES = 1

            def u16tag(self, *_a):
                raise struct_error()

            u32tag = u8tag = u16tag

            def frame_pc(self, _pc):
                raise AssertionError("never reached")

        def struct_error():
            import struct
            return struct.error("no")

        frames, line = ground_empty_trial.frames_for_empty_floor(
            Broken(), environ={ground_empty_trial.GROUND_EMPTY_TRIAL_ENV: "1"})
        self.assertEqual(frames, ())
        self.assertTrue(line.startswith("GROUND_EMPTY_TRIAL_REFUSED "))
        self.assertTrue(line.isascii())


if __name__ == "__main__":
    unittest.main()
