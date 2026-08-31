"""LANE-A: the population handoff the one real crossing owes and does not send.

Every byte-level assertion here is made against the real frozen encoder,
``current/pf_login_game_server_v141.py``, loaded the way the census and
handoff tests load it.  There is no double that makes this module SUCCEED -
the only stand-ins are objects shaped wrongly on purpose, to prove a refusal
fires and to prove WHICH one fired.

THE RULE THIS FILE INHERITS FROM ``test_world_population_handoff``: a refusal
test asserts the refusal BY MESSAGE.  ``assertRaises(Exception)`` around a
broken double also passes when the double failed to be broken, so it cannot
tell "the module refused" from "the test was misspelled".  Everything here is
report-only and nothing raises, so the equivalent is asserting the reason
substring, never merely that a string came back.
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import columbus_quest_dispatch  # noqa: E402
from pirateforce_foundation import world_m2_crossing_handoff as crossing  # noqa: E402
from pirateforce_foundation import world_population_handoff  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


class _EntryWithNoPosition:
    """An entry-shaped object that has no ``position``.  Not a SceneEntry."""


class _EntryWithABadScene:
    """An entry whose position names a scene id the wire cannot carry."""

    class position:  # noqa: N801 - a stand-in attribute, not a class in use
        scene_id = "seventeen"
        x = 0.0
        y = 0.0
        z = 0.0


class CrossingArrivalTests(unittest.TestCase):
    """What the module reads out of a SceneEntry, and what it refuses to."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_reads_the_arrival_scene_and_anchor_from_the_columbus_entry(self):
        entry = columbus_quest_dispatch.resolve_columbus_arrival(
            emit=lambda line: None)
        self.assertEqual(
            crossing.crossing_arrival(entry),
            (columbus_quest_dispatch.COLUMBUS_DEST_SCENE_ID, (0.0, 0.0, 0.0)),
        )

    def test_the_anchor_is_the_position_not_the_stored_row_or_the_fields(self):
        """SceneEntry's own docstring makes ``position`` the source.

        ALL THREE OF ``position``, ``stored`` AND ``teleport_fields`` AGREE
        FOR A SCENE-17 ARRIVAL, so an assertion made against the real entry
        alone passes for any of the three readings and pins none of them.
        That is exactly the shape of test this project has been burned by, so
        this one drives them APART on purpose: ``stored`` is made to name
        Port Royal and ``teleport_fields`` to name scene 99, and the read
        still has to come back 17 with the position's own x/y/z.
        """
        entry = columbus_quest_dispatch.resolve_columbus_arrival(
            emit=lambda line: None)
        lied_to = type(entry)(
            stored=Position(1, 0, -9239.0, -2830.0, 223.0, 0.0),
            position=entry.position,
            destination=entry.destination,
            teleport_fields=(99, 0, 111.0, 222.0, 333.0),
            population_source=entry.population_source,
            return_ticket_required=entry.return_ticket_required,
            relocated=entry.relocated,
            relocation_reason=entry.relocation_reason,
            console_lines=entry.console_lines,
        )
        self.assertEqual(
            crossing.crossing_arrival(lied_to),
            (columbus_quest_dispatch.COLUMBUS_DEST_SCENE_ID, (0.0, 0.0, 0.0)),
        )

    def test_an_entry_with_no_position_is_none_not_a_raise(self):
        self.assertIsNone(crossing.crossing_arrival(_EntryWithNoPosition()))

    def test_a_non_integer_scene_id_is_none_not_a_raise(self):
        self.assertIsNone(crossing.crossing_arrival(_EntryWithABadScene()))


class CrossingHandoffTests(unittest.TestCase):
    """The composed handoff, against the real encoder."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def entry(self):
        return columbus_quest_dispatch.resolve_columbus_arrival(
            emit=lambda line: None)

    def test_the_sea_crossing_composes_a_clear_before_the_teleport(self):
        """The whole reason this module exists, asserted as bytes.

        A clear is what scene 17 owes: the client is holding Port Royal's
        collection, scene 17 has no composable population, and
        ``make_runtime_remote_actors`` replaces rather than merges.  The slot
        matters as much as the kind - a clear belongs to the scene the client
        still renders, so it goes BEFORE the teleport.
        """
        handoff = crossing.crossing_handoff(self.legacy, self.entry())
        self.assertEqual(handoff.kind, world_population_handoff.KIND_CLEAR)
        self.assertEqual(
            handoff.scene_id, columbus_quest_dispatch.COLUMBUS_DEST_SCENE_ID)
        self.assertEqual(
            handoff.dispatch_slot,
            world_population_handoff.SLOT_BEFORE_TELEPORT,
        )
        self.assertTrue(handoff.sends_a_frame)
        self.assertEqual(handoff.actor_count, 0)
        # The bytes are the frozen encoder's, not this module's: the frame
        # must be exactly what the encoder wraps its own pc in.
        self.assertEqual(handoff.frame, self.legacy.frame_pc(handoff.pc))

    def test_the_sea_says_it_is_empty_on_purpose_not_by_omission(self):
        """A decision indistinguishable from an oversight is an oversight.

        Scene 17 used to print ``scene_17_has_no_population_table`` - the same
        string a scene nobody has ever looked at prints.  It is now in
        ``SCENES_INTENTIONALLY_UNPOPULATED`` with the measurement that put it
        there (8 Mob-Set placements, ``n_CLINE_TYPE`` absent, so GT-078's
        rejected reading is the only one available and it stays rejected).
        """
        handoff = crossing.crossing_handoff(self.legacy, self.entry())
        self.assertIn("left_empty_on_purpose", handoff.reason)
        self.assertIn("cline", handoff.reason)
        self.assertNotIn("has_no_population_table", handoff.reason)
        self.assertIn(
            columbus_quest_dispatch.COLUMBUS_DEST_SCENE_ID,
            world_population_handoff.SCENES_INTENTIONALLY_UNPOPULATED,
        )

    def test_a_clear_drops_both_membership_fields_together(self):
        """The pair that cannot be half-taken.

        A caller that queues the clear and leaves the frozen state's
        membership alone can have the whole town recomposed into the new scene
        by one ChooseNPC.  The handoff answers with both fields or neither.
        """
        reset = crossing.crossing_handoff(
            self.legacy, self.entry()).membership_reset
        self.assertTrue(reset.clears_everything)
        self.assertIsNone(reset.population_indices)
        self.assertIsNone(reset.population_refresh_anchor)

    def test_an_unreadable_entry_is_unavailable_and_names_itself(self):
        handoff = crossing.crossing_handoff(
            self.legacy, _EntryWithNoPosition())
        self.assertEqual(
            handoff.kind, world_population_handoff.KIND_UNAVAILABLE)
        self.assertIn(crossing.UNREADABLE_ENTRY, handoff.reason)
        self.assertFalse(handoff.sends_a_frame)
        self.assertEqual(handoff.pc, b"")
        self.assertEqual(handoff.frame, b"")
        # An unavailable handoff still drops the membership, on purpose.
        self.assertTrue(handoff.membership_reset.clears_everything)

    def test_no_legacy_module_is_unavailable_and_does_not_raise(self):
        """The call site as it stands when runtime.py passes nothing."""
        handoff = crossing.crossing_handoff(None, self.entry())
        self.assertEqual(
            handoff.kind, world_population_handoff.KIND_UNAVAILABLE)
        self.assertIn("handoff_not_composed", handoff.reason)


class CrossingConsoleLineTests(unittest.TestCase):
    """The line a human reads off the bridge console."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def entry(self):
        return columbus_quest_dispatch.resolve_columbus_arrival(
            emit=lambda line: None)

    def test_the_default_line_says_the_frame_was_not_dispatched(self):
        """``dispatched=NO`` is a fact about the tree, not a placeholder.

        Nothing queues these bytes today.  The day ``runtime.py`` does, that
        block passes ``dispatched=True`` and this assertion is the one that
        makes the change visible instead of silent.
        """
        line = crossing.crossing_handoff_console_line(
            crossing.crossing_handoff(self.legacy, self.entry()))
        self.assertIn("dispatched=NO", line)
        self.assertIn("composed=YES", line)
        self.assertIn("scene=17", line)
        self.assertIn("kind=clear", line)
        self.assertIn("slot=before_teleport", line)

    def test_dispatched_true_is_the_only_way_to_get_a_yes(self):
        line = crossing.crossing_handoff_console_line(
            crossing.crossing_handoff(self.legacy, self.entry()),
            dispatched=True,
        )
        self.assertIn("dispatched=YES", line)

    def test_the_held_count_is_the_number_the_clear_would_remove(self):
        line = crossing.crossing_handoff_console_line(
            crossing.crossing_handoff(self.legacy, self.entry()),
            held=tuple(range(115)),
        )
        self.assertIn("held=115", line)

    def test_no_held_collection_reads_unmeasured_not_zero(self):
        """0 and "nobody asked" are different answers and must read that way."""
        line = crossing.crossing_handoff_console_line(
            crossing.crossing_handoff(self.legacy, self.entry()))
        self.assertIn("held=unmeasured", line)
        self.assertNotIn("held=0", line)

    def test_an_empty_held_collection_reads_zero_not_unmeasured(self):
        line = crossing.crossing_handoff_console_line(
            crossing.crossing_handoff(self.legacy, self.entry()), held=())
        self.assertIn("held=0", line)
        self.assertNotIn("held=unmeasured", line)

    def test_a_handoff_shaped_object_that_is_not_one_reports_not_raises(self):
        line = crossing.crossing_handoff_console_line(object())
        self.assertTrue(line.startswith(crossing.CONSOLE_TAG + " unreportable"))
        self.assertIn("ValueError", line)

    def test_an_unreadable_held_collection_reports_not_raises(self):
        class _Hostile:
            def __iter__(self):
                raise RuntimeError("not iterable after all")

        line = crossing.crossing_handoff_console_line(
            crossing.crossing_handoff(self.legacy, self.entry()),
            held=_Hostile(),
        )
        self.assertIn("held=unreadable", line)

    def test_every_line_this_module_can_print_is_cp874_encodable(self):
        """The bridge console is cp874.  A report that cannot print is not one.

        Fed a failure whose exception CLASS NAME is non-ASCII on purpose -
        Python 3 allows non-ASCII identifiers, and that is the one place in a
        report line that skips the usual escaping (pf-adversary, round
        2pdf6j, D7, on the stowaway line next door).
        """
        lines = [
            crossing.crossing_handoff_console_line(
                crossing.crossing_handoff(self.legacy, self.entry())),
            crossing.crossing_handoff_console_line(
                crossing.crossing_handoff(self.legacy, _EntryWithNoPosition())),
            crossing.crossing_handoff_console_line(
                crossing.crossing_handoff(None, self.entry())),
            crossing.crossing_handoff_console_line(object()),
        ]
        for line in lines:
            with self.subTest(line=line):
                line.encode("cp874")
                self.assertTrue(all(0x20 <= ord(ch) < 0x7F for ch in line))


class DispatchPrintsTheLineTests(unittest.TestCase):
    """The default path prints it.  No flag, no scenario, no argument."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_a_columbus_crossing_prints_the_crossing_handoff_line_last(self):
        """"Last" was true until the sea-destination round appended one
        more report after it, then the sea-map round appended a second, then
        the trigger-readiness round appended a third -- fixed at
        ``lines[-4]`` now, and this test's own name is kept rather than
        renamed (house rule: strike, do not delete) because a reader hitting
        this exact assertion is the reader who needs the pointer to what
        changed and why."""
        lines = []
        columbus_quest_dispatch.dispatch_columbus_quest3021(
            emit=lines.append, legacy=self.legacy, held_indices=(),
        )
        self.assertTrue(
            lines[-4].startswith(crossing.CONSOLE_TAG + " "), lines)
        self.assertIn("kind=clear", lines[-4])
        self.assertIn("dispatched=NO", lines[-4])
        self.assertTrue(lines[-3].startswith("M2_SEA_DESTINATION "), lines)
        self.assertTrue(lines[-2].startswith("WORLD_M2_SEA_MAP "), lines)
        self.assertTrue(
            lines[-1].startswith("WORLD_M2_TRIGGER_READINESS "), lines)

    def test_the_line_still_prints_when_the_call_site_has_no_legacy(self):
        """The console never goes quiet about a question it cannot answer."""
        lines = []
        columbus_quest_dispatch.dispatch_columbus_quest3021(
            emit=lines.append)
        self.assertTrue(
            lines[-4].startswith(crossing.CONSOLE_TAG + " "), lines)
        self.assertIn("kind=unavailable", lines[-4])
        self.assertIn("composed=NO", lines[-4])

    def test_the_dispatch_still_returns_the_same_scene_entry(self):
        """This round adds a report.  It must not move the crossing."""
        entry = columbus_quest_dispatch.dispatch_columbus_quest3021(
            emit=lambda line: None, legacy=self.legacy, held_indices=(),
        )
        self.assertEqual(entry.teleport_fields, (17, 0, 0.0, 0.0, 0.0))
        self.assertEqual(
            (entry.position.x, entry.position.y, entry.position.z),
            (0.0, 0.0, 0.0),
        )

    def test_the_dispatched_flip_is_reachable_from_the_dispatch_signature(self):
        """The one token the CORE-REQUEST asks the chief's file to pass.

        Without this the console line could never say ``dispatched=YES``: it
        is emitted INSIDE the dispatch, and the queueing happens after the
        dispatch returns, in ``runtime.py``.  A keyword that no test drives is
        a keyword that is wrong on the day it is first used.
        """
        lines = []
        columbus_quest_dispatch.dispatch_columbus_quest3021(
            emit=lines.append, legacy=self.legacy, held_indices=(),
            crossing_handoff_dispatched=True,
        )
        # -4, not -1: the sea-destination round appended one more report
        # after this line, then the sea-map round appended a second, then
        # the trigger-readiness round appended a third -- see
        # test_a_columbus_crossing_prints_the_crossing_handoff_line_last
        # above for the same correction.
        self.assertIn("dispatched=YES", lines[-4])

    def test_the_default_of_that_flip_is_the_truth_about_this_tree(self):
        lines = []
        columbus_quest_dispatch.dispatch_columbus_quest3021(
            emit=lines.append, legacy=self.legacy, held_indices=(),
        )
        self.assertIn("dispatched=NO", lines[-4])

    def test_the_module_is_not_a_scenario_and_is_not_behind_a_flag(self):
        self.assertIs(crossing.production_allowed, True)
        self.assertIs(crossing.test_only, False)


if __name__ == "__main__":
    unittest.main()
