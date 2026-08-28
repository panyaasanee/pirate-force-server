"""The face frame and the census disagree about who placement 1 is.

WHY THIS FILE EXISTS.  On 2026-08-29T00:17+07:00 the owner clicked Columbus
at Port Royal on a flagless boot and the QUEST window that opened was titled
``Sebastian``, with Sebastian's voice and Sebastian's Prison Exile Island
line, while the target panel beside it read ``Columbus`` (attended round
GT-102, notes_to_chief/20260829_0018_KA3A-GT122-PASS-GT102-PARTIAL-GT104-
BLOCKED-mobs-answer-as-npc.md section 2).

The cause is one frame earlier than the conversation:
``make_v98_conversation_face_state`` (``current/pf_login_game_server_v141.py``
1078-1104) resolves each actor through the FROZEN table
``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS``, whose row for placement 1 is
``(1, 2, ..., 'M010_001_000_N', 'Sebastian')``.  It ships that row's second
field - a **Mob-Set number**, not a MOBS id - as the NPCAttr template, ships
Sebastian's avatar basename with it, and drops the row's name field entirely.
So every click re-tags actor 0x2002 as MOBS 2 (Sebastian, Warden) after the
login census correctly told the client it was MOBS 156 (Columbus).

WHERE THE FIX LANDED, AND WHY NOT WHERE IT WAS ASKED FOR (LANE-E, round
c5nwjc, answering LANE-A's CORE-REQUEST of 01:46+07:00).  The CORE-REQUEST
asked for three lines inside the frozen builder.  That was attempted first
and MEASURED to be impossible: the file is immutable by enforcement, not by
convention, and the attempt turned six independent checks red -
``tools/verify_hypothesis_ledger.py``'s ``IMMUTABLE_V141_SHA256``,
``docs/HYPOTHESIS_LEDGER.json`` entries[2], ``test_foundation``'s
``test_v141_characterization_hash``, ``test_item_move_capture``'s
``test_v141_is_still_the_exact_immutable_source``,
``test_second_password_bypass``'s ``test_v141_is_immutable``, and
``test_server_shutdown``'s ``..._v141_is_preserved`` - plus
``test_runtime_console``, which forbids that module printing at all.  So the
frozen builder still carries the defect, ON PURPOSE, and
``src/pirateforce_foundation/world_face_frame.py`` corrects the frame on the
way out of ``runtime``'s dispatch.

THIS FILE THEREFORE PINS BOTH HALVES, and the distinction is the point:

* ``FrozenBuilderStillCarriesTheDefectTests`` - the frozen builder is
  UNCHANGED and still ships Sebastian.  If it ever stops, the frozen file
  moved, and that is news whichever direction it moved in.
* ``RebuiltFaceFrameTests`` - what the client actually receives now ships the
  census identity, read from the bytes.

STILL NOT CLAIMED HERE.  Everything below is wire-layer.  That the owner now
SEES Columbus's window, hears Columbus's voice, and keeps the name line after
a click is client-observable and belongs to ``GT-102``, which the
CORE-REQUEST named as its closer.  No OBSERVER_CONFIRMED is claimed.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_face_frame
from pirateforce_foundation import world_port_royal_identity
from pirateforce_foundation.legacy_bridge import load_legacy

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# The placement the owner clicked.  0x2000 + index + 1 is this project's one
# actor-identity formula (population.py), so index 1 is actor 0x2002.
COLUMBUS_PLACEMENT_INDEX = 1
COLUMBUS_ACTOR_IDENTITY = 0x2000 + COLUMBUS_PLACEMENT_INDEX + 1
COLUMBUS_MOBS_N_ID = 156
SEBASTIAN_MOBS_N_ID = 2
# Mob-Set 1.  Its CLINE leader 155 has no CONSTDATA MOBS row, so it has no
# avatar to ship; ``census_order`` drops it at login.
UNRESOLVABLE_PLACEMENT_INDEX = 0


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class FrozenFaceFrameRowTests(unittest.TestCase):
    """What the frozen table says about placement 1 today."""

    def setUp(self):
        self.legacy = _legacy()
        self.row = {
            row[0]: row
            for row in self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        }[COLUMBUS_PLACEMENT_INDEX]

    def test_the_frozen_row_for_placement_1_is_labelled_sebastian(self):
        # Field 1 is a Mob-Set number and field 6 is the pre-RE-128 label.
        # If this ever changes, the frozen file moved and that is news.
        self.assertEqual(self.row[1], 2)
        self.assertEqual(self.row[6], "Sebastian")

    def test_that_row_field_is_a_mob_set_number_not_a_mobs_id(self):
        # The number 2 is BOTH a valid Mob-Set number here and a real MOBS
        # n_ID elsewhere (Sebastian's).  That collision is why shipping the
        # Mob-Set number as an identity is not a visibly wrong number - it is
        # a visibly wrong PERSON, which is what the owner saw.
        identity = world_port_royal_identity.resolve(self.row[1])
        self.assertIsNotNone(identity, "Mob-Set 2 must resolve at all")
        self.assertEqual(identity.mobs_n_id, COLUMBUS_MOBS_N_ID)
        self.assertEqual(identity.name, "Columbus")
        self.assertNotEqual(
            identity.mobs_n_id, SEBASTIAN_MOBS_N_ID,
            "placement 1 is Columbus; MOBS 2 is Sebastian the Warden",
        )


class FrozenBuilderStillCarriesTheDefectTests(unittest.TestCase):
    """The frozen builder is UNCHANGED, and that is deliberate.

    These assertions read the BYTES the frozen builder produces.  They are
    not a claim that the defect is acceptable - they are the pin that says
    the fix was applied downstream and NOT by editing a file six checks
    forbid editing.  If one of these fails, someone changed the frozen file:
    stop and read ``world_face_frame``'s docstring before doing anything
    else, because the ledger and four other tests are about to go red too.
    """

    def setUp(self):
        self.legacy = _legacy()
        face, idx = self.legacy.make_v98_conversation_face_state(
            (UNRESOLVABLE_PLACEMENT_INDEX, COLUMBUS_PLACEMENT_INDEX),
            COLUMBUS_ACTOR_IDENTITY, 100.0, 200.0,
        )
        self.assertEqual(idx, COLUMBUS_PLACEMENT_INDEX)
        _pc, self.frame = face

    def test_the_frozen_frame_still_carries_sebastians_identity(self):
        attr = self.legacy.make_npc_attr(
            SEBASTIAN_MOBS_N_ID, COLUMBUS_ACTOR_IDENTITY, 1, 0,
            "M010_001_000_N",
        )
        self.assertIn(
            attr, self.frame,
            "the frozen builder stopped shipping MOBS 2 for actor 0x2002 - "
            "the immutable file moved; see world_face_frame's docstring",
        )

    def test_the_frozen_builder_still_drops_the_name_field(self):
        """``make_npc_attr`` sets BasicAttr bit 0x0001 only for a truthy
        ``basic_name``, and the frozen call site passes none - so the field
        is ABSENT, not empty.  The rebuilt frame supplies it; this pins that
        the frozen one still does not, so the two cannot be confused."""
        source = LEGACY_PATH.read_text(encoding="utf-8")
        call = "make_npc_attr(template_id, aid, 1, 0, preset)"
        self.assertEqual(
            source.count(call), 1,
            "the face-frame call site moved or multiplied; re-read the "
            "builder before trusting anything else in this file",
        )


class RebuiltFaceFrameTests(unittest.TestCase):
    """What the CLIENT receives, after ``runtime`` rebuilds the frame.

    Read from the bytes, not from the table the builder reads.  An earlier
    version of this file read the table instead, and pf-adversary proved the
    difference by applying the prescribed fix: the tests stayed green while
    the wire changed.  A detector that cannot see the thing it detects is
    worse than no detector, because it is quoted as one.
    """

    def setUp(self):
        self.legacy = _legacy()
        self.indices = (UNRESOLVABLE_PLACEMENT_INDEX, COLUMBUS_PLACEMENT_INDEX)
        _pc, self.frame = world_face_frame.build_face_state(
            self.legacy, self.indices, COLUMBUS_PLACEMENT_INDEX, 100.0, 200.0,
        )

    def _attr(self, template_id, preset, name=""):
        return self.legacy.make_npc_attr(
            template_id, COLUMBUS_ACTOR_IDENTITY, 1, 0, preset,
            basic_name=name,
        )

    def test_the_rebuilt_frame_ships_the_census_identity(self):
        identity = world_port_royal_identity.resolve(2)
        self.assertIn(
            self._attr(identity.mobs_n_id, identity.outfit, identity.name),
            self.frame,
            "the rebuilt face frame stopped carrying the resolved census "
            "identity for actor 0x2002 - the GT-102 defect is back",
        )

    def test_the_rebuilt_frame_does_not_ship_sebastian(self):
        self.assertNotIn(
            self._attr(SEBASTIAN_MOBS_N_ID, "M010_001_000_N"), self.frame,
            "the rebuilt frame is shipping MOBS 2 (Sebastian the Warden) "
            "for the actor the census called Columbus - this is the exact "
            "wire the owner saw at 2026-08-29T00:17+07:00",
        )

    def test_the_two_frames_now_agree_on_who_this_actor_is(self):
        """The whole point, stated once: census entry == face-frame entry.

        Built through ``world_population``'s own resolver call rather than by
        restating the expected bytes, so this cannot drift into agreeing
        with itself while both sides are wrong together.
        """
        identity = world_port_royal_identity.resolve(2)
        census_attr = self.legacy.make_npc_attr(
            identity.mobs_n_id, COLUMBUS_ACTOR_IDENTITY, 1, 0,
            identity.outfit, basic_name=identity.name,
        )
        self.assertIn(census_attr, self.frame)

    def test_an_unresolvable_placement_is_omitted_not_renumbered(self):
        """P0 is in the requested indices and must not be in the frame.

        Asserted by rebuilding P0's NPCAttr under BOTH numbering schemes and
        requiring neither in the frame, rather than by hunting for two loose
        bytes that a float or a length prefix could supply by accident.
        """
        self.assertIsNone(world_port_royal_identity.resolve(1))
        p0_aid = 0x2000 + UNRESOLVABLE_PLACEMENT_INDEX + 1
        row = {
            r[0]: r for r in self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        }[UNRESOLVABLE_PLACEMENT_INDEX]
        self.assertNotIn(
            self.legacy.make_npc_attr(row[1], p0_aid, 1, 0, row[5]),
            self.frame,
            "the unresolvable placement came back under its Mob-Set number",
        )
        self.assertEqual(
            world_face_frame.omitted_indices(self.legacy, self.indices),
            (UNRESOLVABLE_PLACEMENT_INDEX,),
        )

    def test_a_click_on_an_unresolvable_actor_is_refused_not_faked(self):
        with self.assertRaises(ValueError):
            world_face_frame.build_face_state(
                self.legacy, self.indices, UNRESOLVABLE_PLACEMENT_INDEX,
                100.0, 200.0,
            )

    def test_the_selected_actor_still_gets_its_movement_attr(self):
        """The rebuild must not lose what V98 exists to send.

        V95 proved mask 0x02 teleports the NPC; V98's whole purpose is the
        mask 0x03 MovementAttr with authentic XYZ and a computed heading.
        An identity fix that dropped it would trade a visible bug for a
        worse invisible one.
        """
        row = {
            r[0]: r for r in self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        }[COLUMBUS_PLACEMENT_INDEX]
        _, _tid, px, py, pz, _preset, _name = row
        heading = self.legacy._heading_to_player(px, py, 100.0, 200.0)
        self.assertIn(
            self.legacy.make_remote_movement_attr(
                COLUMBUS_ACTOR_IDENTITY, px, py, pz, heading, mask=0x03,
            ),
            self.frame,
        )


class RebuildIsTotalAndAdditiveTests(unittest.TestCase):
    """``rebuild_face_actions`` is called on EVERY dispatch, so it must be a
    no-op for everything that is not a face frame."""

    def setUp(self):
        self.legacy = _legacy()
        self.indices = (UNRESOLVABLE_PLACEMENT_INDEX, COLUMBUS_PLACEMENT_INDEX)
        self.pos = (100.0, 200.0, 0.0, 0.0)

    def test_an_action_list_with_no_face_frame_is_returned_unchanged(self):
        events = []
        actions = [
            ("SOME_OTHER_ACTION", b"\x01", b"\x02", 0.0),
            ("V98_SOMETHING_ELSE_ENTIRELY", b"\x03", b"\x04", 0.35),
        ]
        self.assertEqual(
            world_face_frame.rebuild_face_actions(
                self.legacy, list(actions), self.indices, self.pos, events,
            ),
            actions,
        )
        self.assertEqual(events, [])

    def test_a_face_action_is_rebuilt_and_keeps_its_label_and_delay(self):
        events = []
        label = (
            "V98_NPC_FACE_PLAYER_POSITION_HEADING_P"
            f"{COLUMBUS_PLACEMENT_INDEX}"
        )
        stale_pc, stale_frame = self.legacy.make_v98_conversation_face_state(
            self.indices, COLUMBUS_ACTOR_IDENTITY, 100.0, 200.0,
        )[0]
        out = world_face_frame.rebuild_face_actions(
            self.legacy, [(label, stale_pc, stale_frame, 0.25)],
            self.indices, self.pos, events,
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0][0], label)
        self.assertEqual(out[0][3], 0.25)
        self.assertNotEqual(
            out[0][2], stale_frame,
            "the action came back with the frozen builder's bytes",
        )
        self.assertIn(f"face_frame_identity_resolved_p{COLUMBUS_PLACEMENT_INDEX}",
                      events)

    def test_the_harness_label_is_rebuilt_too(self):
        """Both labels the frozen branch emits reach the client the same way,
        so fixing only one would leave the shop-trigger click still wrong."""
        events = []
        label = f"V112_TEST_HARNESS_FACE_PLAYER_P{COLUMBUS_PLACEMENT_INDEX}"
        out = world_face_frame.rebuild_face_actions(
            self.legacy, [(label, b"", b"", 0.0)], self.indices, self.pos,
            events,
        )
        self.assertEqual(out[0][0], label)
        self.assertNotEqual(out[0][2], b"")

    def test_nothing_is_rebuilt_before_the_population_is_armed(self):
        events = []
        actions = [("V98_NPC_FACE_PLAYER_POSITION_HEADING_P1", b"", b"", 0.0)]
        self.assertEqual(
            world_face_frame.rebuild_face_actions(
                self.legacy, list(actions), None, self.pos, events,
            ),
            actions,
        )
        self.assertEqual(
            world_face_frame.rebuild_face_actions(
                self.legacy, list(actions), self.indices, None, events,
            ),
            actions,
        )

    def test_a_label_that_only_looks_like_one_is_left_alone(self):
        """``..._P`` with no number, or a trailing word, is not a face frame.

        Guards the label parse itself: a prefix match without the digit check
        would rebuild an unrelated action and destroy its frame.
        """
        events = []
        for label in (
            "V98_NPC_FACE_PLAYER_POSITION_HEADING_P",
            "V98_NPC_FACE_PLAYER_POSITION_HEADING_PLAYER",
            "V112_TEST_HARNESS_FACE_PLAYER_P1X",
        ):
            self.assertFalse(world_face_frame.is_face_label(label), label)
            actions = [(label, b"keep", b"keep", 0.0)]
            self.assertEqual(
                world_face_frame.rebuild_face_actions(
                    self.legacy, list(actions), self.indices, self.pos,
                    events,
                ),
                actions,
            )


if __name__ == "__main__":
    unittest.main()
