"""LANE-A: the generation that belongs to the scene you just arrived in.

Every byte-level assertion in this file is made against the real frozen
encoder, ``current/pf_login_game_server_v141.py``, loaded the way the census
tests load it.  Doubles appear in exactly one place - the sabotage class - and
only to make the encoder MISBEHAVE, never to make it succeed.  Round e7q6yy
lost a whole adversary pass to a double that was kinder to this lane than the
real object was.

THE SECOND RULE THIS FILE FOLLOWS, added after the adversary pass of round
k69t3b mutated the module and watched three mutants survive: a refusal test
asserts WHICH refusal fired, by message.  ``assertRaises(Exception)`` around a
sabotage double also passes when the double failed to recognise its own mode,
so it cannot tell "the module refused" from "the test was misspelled".
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.world_population import (  # noqa: E402
    CENSUS_COUNT,
    INITIAL_REAPPLY_MS,
    WIRE_COUNT_TAG_OFFSET,
    WIRE_HEADER_BYTES,
    build_world_population,
)
from pirateforce_foundation.world_population_handoff import (  # noqa: E402
    KIND_CENSUS,
    KIND_CLEAR,
    KIND_UNAVAILABLE,
    LABEL_CENSUS,
    LABEL_CLEAR,
    LABEL_UNAVAILABLE,
    SLOT_AFTER_TELEPORT,
    SLOT_BEFORE_TELEPORT,
    SLOT_NOT_APPLICABLE,
    SceneHandoff,
    build_clear_generation,
    handoff_console_line,
    handoff_for_arrival,
    handoff_on_crossing,
    handoff_report,
    wire_count_of,
)

LEGACY_PATH = ROOT / "current/pf_login_game_server_v141.py"

# Every scene pinned in scenarios/world_scene_registry_001.json except home.
# 2 is the one this project has actually rendered besides Port Royal, 278 is
# the M2 stage, 997 is the pinned candidate COO-DECISION 0550 did not choose.
# None has a population table, and none may receive the dock census.
NON_HOME_SCENES = (2, 278, 997)

# Each mode is a way the frozen encoder could drift or be replaced such that a
# frame this module calls a clear is not one, paired with the fragment of the
# refusal that has to fire for it.  The pairing is the point: it pins WHICH
# check caught it, so a check that stops catching anything shows up as a red
# test rather than as a mode some other check happens to cover.
SABOTAGE = {
    "raises": "encoder is gone",
    "not_a_pair": r"did not return \(pc, frame\)",
    "not_bytes": "not bytes",
    "empty_frame": "carries no frame",
    "foreign_frame": "does not match its own pc",
    "no_header": "expected collection header",
    # A real three-actor collection: its frame IS its own pc's frame, so the
    # pair check passes and the COUNT check is what refuses it.
    "counts_actors": "declares 3 actors",
    "lying_header": "declares 3 actors",
    "body_behind_zero": "bytes of body behind a zero count",
}


class _SabotagedEncoder:
    """A legacy stand-in whose ONLY job is to encode the clear frame wrongly.

    The client reads the count in the header and then reads that many actor
    bodies, so a header that lies is not cosmetic - it is the stream-tail
    misalignment this client answers with ErrorData=28317.

    An unknown mode raises at construction, not at call time: a mode name
    misspelled in a test must fail that test, not be absorbed by the module's
    own refusal path and read as a pass.
    """

    def __init__(self, mode: str, real):
        if mode not in SABOTAGE:
            raise AssertionError(f"unknown sabotage mode {mode!r}")
        self.mode = mode
        self.real = real
        self.calls = 0

    def make_runtime_remote_actors(self, entries):
        self.calls += 1
        if self.mode == "raises":
            raise RuntimeError("encoder is gone")
        if self.mode == "not_a_pair":
            return b"only-one-thing"
        if self.mode == "not_bytes":
            return ("pc", "frame")
        if self.mode == "empty_frame":
            pc, _ = self.real.make_runtime_remote_actors(())
            return (pc, b"")
        if self.mode == "foreign_frame":
            # The defect the pc-side checks cannot see at all: a valid empty
            # header, and the CENSUS on the wire behind it.  Only the frame
            # is sent (v141:7755), so every count read off the pc is a read of
            # a buffer the client never receives.
            pc, _ = self.real.make_runtime_remote_actors(())
            _, census_frame = self.real.make_v112_monster_shop_population_state()[:2]
            return (pc, census_frame)
        if self.mode == "no_header":
            pc = b"\x00" * WIRE_HEADER_BYTES
            return (pc, self.real.frame_pc(pc))
        if self.mode == "counts_actors":
            # The clear that quietly became a census: a real three-actor
            # collection returned for a request for none.
            return self.real.make_v112_monster_shop_population_state()[:2]
        if self.mode == "lying_header":
            # Header-length pc whose count field claims three actors with no
            # bodies behind it.  The ONLY check that can catch this is the
            # count check - the length check sees 17 bytes and is happy.
            pc, _ = self.real.make_runtime_remote_actors(())
            lying = bytearray(pc)
            lying[WIRE_COUNT_TAG_OFFSET + 1:WIRE_COUNT_TAG_OFFSET + 3] = (
                (3).to_bytes(2, "little")
            )
            pc = bytes(lying)
            return (pc, self.real.frame_pc(pc))
        if self.mode == "body_behind_zero":
            pc, _ = self.real.make_runtime_remote_actors(())
            pc = pc + b"\x99\x99\x99"
            return (pc, self.real.frame_pc(pc))
        raise AssertionError(f"unhandled sabotage mode {self.mode}")

    def __getattr__(self, name):
        return getattr(self.real, name)


class HandoffTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.anchor = (
            cls.legacy.V135_PLAYER_X,
            cls.legacy.V135_PLAYER_Y,
            cls.legacy.V135_PLAYER_Z,
        )
        cls.far_anchor = (
            cls.legacy.V112_PLAYER_X,
            cls.legacy.V112_PLAYER_Y,
            cls.legacy.V112_PLAYER_Z,
        )

    # ---- the clear frame, measured on the frozen encoder -----------------

    def test_the_clear_frame_is_a_collection_that_declares_no_actors(self):
        pc, frame = build_clear_generation(self.legacy)
        self.assertEqual(len(pc), WIRE_HEADER_BYTES)
        self.assertEqual(wire_count_of(pc), 0)
        self.assertTrue(frame)

    def test_the_bytes_that_are_sent_are_the_bytes_that_were_checked(self):
        """v141:7755 sends the frame; every other check in the module reads pc.

        Without this the module could validate an empty header and ship a
        census behind it, which is the sabotage mode ``foreign_frame``.
        """
        pc, frame = build_clear_generation(self.legacy)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        census = handoff_for_arrival(self.legacy, 1, self.anchor)
        self.assertEqual(census.frame, self.legacy.frame_pc(census.pc))

    def test_the_clear_frame_does_not_depend_on_where_the_player_stands(self):
        """A clear is the same bytes from anywhere; only a census is anchored."""
        first = handoff_for_arrival(self.legacy, 278, self.anchor)
        second = handoff_for_arrival(self.legacy, 278, self.far_anchor)
        self.assertEqual(first.pc, second.pc)
        self.assertEqual(first.frame, second.frame)

    def test_every_scene_without_a_population_table_gets_the_clear(self):
        for scene in NON_HOME_SCENES:
            with self.subTest(scene=scene):
                handoff = handoff_for_arrival(self.legacy, scene, self.anchor)
                self.assertEqual(handoff.kind, KIND_CLEAR)
                self.assertEqual(handoff.actor_count, 0)
                self.assertEqual(handoff.membership, ())
                self.assertEqual(wire_count_of(handoff.pc), 0)
                self.assertIsNone(handoff.generation)
                self.assertIsNone(handoff.reapply_ms)
                self.assertEqual(handoff.label, LABEL_CLEAR.format(scene))
                self.assertTrue(handoff.sends_a_frame)

    def test_the_dock_census_can_never_be_the_answer_for_another_scene(self):
        """The refusal that matters most, checked at the bytes not the branch.

        A census delivered into scene 278 is 115 Port Royal NPCs standing in a
        football field at bg0001 coordinates.  No non-home scene may come back
        with a frame that declares actors, whatever the caller asked for.
        """
        for scene in NON_HOME_SCENES:
            for requested in (None, 3, CENSUS_COUNT):
                with self.subTest(scene=scene, actor_count=requested):
                    handoff = handoff_for_arrival(
                        self.legacy, scene, self.anchor, actor_count=requested
                    )
                    self.assertEqual(wire_count_of(handoff.pc), 0)

    # ---- ordering --------------------------------------------------------

    def test_the_removal_goes_before_the_teleport_and_the_addition_after(self):
        """The ordering rule lives on the object, not in prose to remember.

        The clear belongs to the scene the client is still in - the only state
        anyone has observed omission behave in.  The census belongs to the
        scene it is going to, or 115 actors tagged scene 1 arrive while the
        client still renders 278.
        """
        for scene in NON_HOME_SCENES:
            with self.subTest(scene=scene):
                self.assertEqual(
                    handoff_for_arrival(self.legacy, scene, self.anchor).dispatch_slot,
                    SLOT_BEFORE_TELEPORT,
                )
        self.assertEqual(
            handoff_for_arrival(self.legacy, 1, self.anchor).dispatch_slot,
            SLOT_AFTER_TELEPORT,
        )
        self.assertEqual(
            handoff_on_crossing(None, 278, self.anchor).dispatch_slot,
            SLOT_NOT_APPLICABLE,
        )

    # ---- the home return -------------------------------------------------

    def test_the_return_generation_is_the_census_module_s_own_frame(self):
        """Deliberately narrow: this proves the module delegates, nothing more.

        It does NOT prove equivalence with the login path - nothing in this
        repository composes that path today (`WORLD_CENSUS_INITIAL_` is in an
        unmerged PR), so an equivalence claim here would be a claim about code
        that is not in the tree.  A regression inside ``build_world_population``
        moves both sides of this assertion equally, and that is what
        ``tests/test_world_population.py`` is for.
        """
        handoff = handoff_for_arrival(self.legacy, 1, self.anchor)
        direct = build_world_population(
            self.legacy, self.anchor, CENSUS_COUNT, scene_id=1,
            count_source="full_census",
        )
        self.assertEqual(handoff.kind, KIND_CENSUS)
        self.assertEqual(handoff.pc, direct.pc)
        self.assertEqual(handoff.frame, direct.frame)
        self.assertEqual(handoff.actor_count, CENSUS_COUNT)
        self.assertEqual(wire_count_of(handoff.pc), CENSUS_COUNT)
        self.assertEqual(handoff.reapply_ms, INITIAL_REAPPLY_MS)
        self.assertEqual(handoff.label, LABEL_CENSUS.format(1))

    def test_the_return_census_stands_the_town_around_where_you_came_back_in(self):
        """Membership is the whole census; ORDER is anchored to the arrival."""
        near = handoff_for_arrival(self.legacy, 1, self.anchor)
        far = handoff_for_arrival(self.legacy, 1, self.far_anchor)
        self.assertEqual(set(near.membership), set(far.membership))
        self.assertNotEqual(near.membership, far.membership)
        self.assertNotEqual(near.pc, far.pc)

    def test_the_membership_the_caller_needs_for_population_indices_is_offered(self):
        """v141:4396-4420 answers ChooseNPC for anything in that set.

        A caller that queues a clear and leaves the set alone can have the
        whole town recomposed into the new scene by one click; the set is
        runtime.py's, but it cannot be corrected without this list.
        """
        census = handoff_for_arrival(self.legacy, 1, self.anchor)
        self.assertEqual(len(census.membership), CENSUS_COUNT)
        self.assertEqual(handoff_report(census)["membership"], census.membership)
        clear = handoff_for_arrival(self.legacy, 278, self.anchor)
        self.assertEqual(handoff_report(clear)["membership"], ())

    def test_a_caller_chosen_count_is_recorded_as_the_callers(self):
        """CHARTER-02: a short frame arrives with its reason attached."""
        handoff = handoff_for_arrival(self.legacy, 1, self.anchor, actor_count=3)
        report = handoff_report(handoff)
        self.assertEqual(report["actor_count"], 3)
        self.assertEqual(report["wire_actor_count"], 3)
        self.assertEqual(report["census"]["count_source"], "caller_requested")
        self.assertEqual(report["census"]["shortfall_reason"], "caller_requested=3")

    # ---- the frame path must never raise ---------------------------------

    def test_the_crossing_entry_point_does_not_raise_on_anything(self):
        """The contract that the last round of this lane broke by omission."""
        cases = (
            ("legacy_none", None, 278, self.anchor, {}),
            ("scene_is_a_string", self.legacy, "278", self.anchor, {}),
            ("scene_is_a_bool", self.legacy, True, self.anchor, {}),
            ("scene_is_zero", self.legacy, 0, self.anchor, {}),
            ("scene_out_of_range", self.legacy, 0x10000, self.anchor, {}),
            ("scene_is_non_ascii", self.legacy, "日本", self.anchor, {}),
            ("anchor_is_none", self.legacy, 1, None, {}),
            ("anchor_is_short", self.legacy, 1, (1.0, 2.0), {}),
            ("anchor_has_a_string", self.legacy, 1, (1.0, 2.0, "z"), {}),
            ("anchor_is_non_ascii", self.legacy, 1, (1.0, 2.0, "位"), {}),
            ("anchor_is_a_list", self.legacy, 1, [1.0, 2.0, 3.0], {}),
            ("anchor_is_nan_free_but_huge", self.legacy, 1, (1e40, 0.0, 0.0), {}),
            ("count_is_a_string", self.legacy, 1, self.anchor,
             {"actor_count": "three"}),
            ("count_is_a_bool", self.legacy, 1, self.anchor,
             {"actor_count": True}),
            ("count_is_zero", self.legacy, 1, self.anchor, {"actor_count": 0}),
            ("count_is_negative", self.legacy, 1, self.anchor,
             {"actor_count": -5}),
            ("count_is_over_the_census", self.legacy, 1, self.anchor,
             {"actor_count": 10_000}),
        )
        for name, legacy, scene, anchor, kwargs in cases:
            with self.subTest(case=name):
                handoff = handoff_on_crossing(legacy, scene, anchor, **kwargs)
                self.assertEqual(handoff.kind, KIND_UNAVAILABLE)
                self.assertEqual(handoff.pc, b"")
                self.assertEqual(handoff.frame, b"")
                self.assertFalse(handoff.sends_a_frame)
                self.assertEqual(handoff.dispatch_slot, SLOT_NOT_APPLICABLE)
                self.assertEqual(handoff.label, LABEL_UNAVAILABLE)
                self.assertTrue(handoff.reason.startswith("handoff_not_composed:"))
                handoff_console_line(handoff).encode("ascii")

    def test_an_exception_whose_message_cannot_be_printed_is_still_printed(self):
        """A refusal a cp874 console cannot encode is a refusal nobody reads.

        Two shapes: a message with characters outside ASCII, and one with a
        bare CR, which on a Windows console rewrites the line it was meant to
        add rather than appearing beneath it.
        """

        class _Rude:
            def __init__(self, text):
                self.text = text

            def make_runtime_remote_actors(self, entries):
                raise RuntimeError(self.text)

        for name, text in (
            ("non_ascii", "เสีย"),
            ("carriage_return", "line one\rline two"),
            ("newline", "line one\nline two"),
        ):
            with self.subTest(case=name):
                handoff = handoff_on_crossing(_Rude(text), 278, self.anchor)
                self.assertEqual(handoff.kind, KIND_UNAVAILABLE)
                line = handoff_console_line(handoff)
                line.encode("ascii")
                line.encode("cp874")
                self.assertNotIn("\r", line)
                self.assertNotIn("\n", line)

    def test_an_exception_whose_str_itself_raises_is_still_a_refusal(self):
        class _Unprintable(Exception):
            def __str__(self):
                raise ValueError("even the message is broken")

        class _Worse:
            def make_runtime_remote_actors(self, entries):
                raise _Unprintable()

        handoff = handoff_on_crossing(_Worse(), 278, self.anchor)
        self.assertEqual(handoff.kind, KIND_UNAVAILABLE)
        self.assertIn("unprintable", handoff.reason)
        handoff_console_line(handoff).encode("ascii")

    def test_an_interrupt_is_not_swallowed(self):
        """The one deliberate hole in "never raises", pinned so it stays one.

        A frame handler that eats KeyboardInterrupt is a process the operator
        cannot stop at the moment they are trying to stop it.
        """

        class _Interrupts:
            def make_runtime_remote_actors(self, entries):
                raise KeyboardInterrupt()

        with self.assertRaises(KeyboardInterrupt):
            handoff_on_crossing(_Interrupts(), 278, self.anchor)

    def test_the_console_helper_does_not_raise_either(self):
        """It is called from the same block, to print the refusal."""
        for bad in (None, 42, "handoff", object(), b""):
            with self.subTest(value=repr(bad)[:20]):
                line = handoff_console_line(bad)
                self.assertIn("WORLD_POP_HANDOFF", line)
                line.encode("ascii")

    def test_an_encoder_that_misbehaves_refuses_by_the_check_that_owns_it(self):
        """Each sabotage pinned to the refusal that must catch it.

        Not ``assertRaises(Exception)``: that passes when a check has stopped
        firing and some other one happens to cover the mode, which is how the
        first version of this file let a deleted count check survive.
        """
        for mode, expected in SABOTAGE.items():
            with self.subTest(mode=mode):
                sabotaged = _SabotagedEncoder(mode, self.legacy)
                with self.assertRaisesRegex(Exception, expected):
                    build_clear_generation(sabotaged)
                self.assertEqual(sabotaged.calls, 1)
                handoff = handoff_on_crossing(sabotaged, 278, self.anchor)
                self.assertEqual(handoff.kind, KIND_UNAVAILABLE)
                self.assertEqual(handoff.pc, b"")
                self.assertFalse(handoff.sends_a_frame)

    def test_a_header_that_promises_bodies_it_does_not_carry_is_refused(self):
        """The count check's own case, which no length check can see.

        17 bytes, a valid tag, a frame that really is this pc's frame - and a
        count field that says three actors follow.  A client told three bodies
        follow and given none is the stream-tail misalignment answered with
        ErrorData=28317.
        """
        sabotaged = _SabotagedEncoder("lying_header", self.legacy)
        pc, frame = sabotaged.make_runtime_remote_actors(())
        self.assertEqual(len(pc), WIRE_HEADER_BYTES)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(wire_count_of(pc), 3)
        with self.assertRaisesRegex(ValueError, "declares 3 actors"):
            build_clear_generation(sabotaged)

    def test_the_clear_that_quietly_became_a_census_is_the_one_that_matters(self):
        """Queued as a clear it would not despawn the town - it would replace
        the town with three dock NPCs standing in the scene just walked into.
        """
        sabotaged = _SabotagedEncoder("counts_actors", self.legacy)
        raw_pc, _ = sabotaged.make_runtime_remote_actors(())
        self.assertGreater(wire_count_of(raw_pc), 0)
        handoff = handoff_on_crossing(sabotaged, 278, self.anchor)
        self.assertEqual(handoff.kind, KIND_UNAVAILABLE)

    def test_nothing_on_the_crossing_path_reads_the_disk(self):
        """Remove every read this process has, then cross both ways.

        A disk read inside a frame handler is a stall on a serial server.  This
        is a weak test on purpose - it is true today because the placements
        come off the legacy module's attributes and ``population_source`` is an
        integer compare - and it is here so that a future version that reaches
        for a file cannot do it quietly.
        """
        import builtins
        import io

        originals = (Path.read_text, Path.read_bytes, Path.open,
                     builtins.open, io.open)
        reads = []

        def refuse(target, *args, **kwargs):
            reads.append(str(target))
            raise AssertionError(f"the crossing path read {target}")

        Path.read_text = refuse
        Path.read_bytes = refuse
        Path.open = refuse
        builtins.open = refuse
        io.open = refuse
        try:
            out = handoff_for_arrival(self.legacy, 278, self.anchor)
            home = handoff_for_arrival(self.legacy, 1, self.anchor)
        finally:
            (Path.read_text, Path.read_bytes, Path.open,
             builtins.open, io.open) = originals
        self.assertEqual(reads, [])
        self.assertEqual(out.kind, KIND_CLEAR)
        self.assertEqual(home.kind, KIND_CENSUS)

    # ---- the console line ------------------------------------------------

    def test_the_line_reports_the_bytes_and_not_the_intent(self):
        """A handoff whose kind and whose header disagree must print both.

        Nothing in the module can construct this; it is assembled by hand
        precisely because the check exists for the day something else can.
        """
        real = handoff_for_arrival(self.legacy, 1, self.anchor)
        lying = SceneHandoff(
            scene_id=278, kind=KIND_CLEAR, reason="hand_built_for_this_test",
            label=LABEL_CLEAR.format(278), actor_count=0,
            pc=real.pc, frame=real.frame, reapply_ms=None,
            dispatch_slot=SLOT_BEFORE_TELEPORT, generation=None,
        )
        line = handoff_console_line(lying)
        self.assertIn("kind=clear", line)
        self.assertIn("actors=0", line)
        self.assertIn("wire=%d" % CENSUS_COUNT, line)

    def test_an_unreadable_header_says_so_rather_than_guessing_a_count(self):
        broken = SceneHandoff(
            scene_id=278, kind=KIND_CLEAR, reason="hand_built_for_this_test",
            label=LABEL_CLEAR.format(278), actor_count=0,
            pc=b"\x00" * WIRE_HEADER_BYTES, frame=b"\x00" * 8,
            reapply_ms=None, dispatch_slot=SLOT_BEFORE_TELEPORT,
            generation=None,
        )
        self.assertEqual(handoff_report(broken)["wire_actor_count"], "UNREADABLE")
        self.assertIn("wire=UNREADABLE", handoff_console_line(broken))

    def test_every_string_this_module_can_print_is_ascii(self):
        """The bridge console is cp874; a non-ASCII byte there is a crash.

        Covers the labels too - the first version of this test only exercised
        lines, so a non-ASCII label survived a mutation run untouched.
        """
        strings = [
            LABEL_UNAVAILABLE,
            LABEL_CENSUS.format(1),
            LABEL_CLEAR.format(278),
            handoff_console_line(handoff_for_arrival(self.legacy, 1, self.anchor)),
            handoff_console_line(handoff_for_arrival(self.legacy, 278, self.anchor)),
            handoff_console_line(handoff_on_crossing(None, 278, self.anchor)),
            handoff_console_line(handoff_on_crossing(self.legacy, "x", self.anchor)),
        ]
        for text in strings:
            with self.subTest(text=text[:40]):
                text.encode("ascii")
                text.encode("cp874")
                self.assertNotIn("\n", text)
                self.assertNotIn("\r", text)

    def test_the_report_carries_the_census_own_count_not_a_second_one(self):
        handoff = handoff_for_arrival(self.legacy, 1, self.anchor)
        report = handoff_report(handoff)
        self.assertTrue(report["census"]["counts_agree"])
        self.assertTrue(report["census"]["bodies_intact"])
        self.assertEqual(report["census"]["assembled_count"], CENSUS_COUNT)
        self.assertEqual(report["wire_actor_count"], CENSUS_COUNT)
        clear = handoff_report(handoff_for_arrival(self.legacy, 278, self.anchor))
        self.assertIsNone(clear["census"])

    def test_a_handoff_with_no_bytes_is_not_queueable_whatever_its_kind_says(self):
        """``sends_a_frame`` reads the bytes, so a mislabelled kind cannot send.

        The hand-built case is the mutation that survived the first version of
        this file: ``sends_a_frame`` returning on ``kind`` alone.
        """
        refused = handoff_on_crossing(None, 278, self.anchor)
        self.assertFalse(refused.sends_a_frame)
        empty_but_labelled = SceneHandoff(
            scene_id=278, kind=KIND_CLEAR, reason="hand_built_for_this_test",
            label=LABEL_CLEAR.format(278), actor_count=0, pc=b"", frame=b"",
            reapply_ms=None, dispatch_slot=SLOT_BEFORE_TELEPORT,
            generation=None,
        )
        self.assertFalse(empty_but_labelled.sends_a_frame)
        for scene in (1,) + NON_HOME_SCENES:
            with self.subTest(scene=scene):
                self.assertTrue(
                    handoff_for_arrival(self.legacy, scene, self.anchor).sends_a_frame
                )


if __name__ == "__main__":
    unittest.main()
