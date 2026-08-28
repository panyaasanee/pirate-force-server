"""The face frame and the census disagree about who placement 1 is.

WHY THIS FILE EXISTS.  On 2026-08-29T00:17+07:00 the owner clicked Columbus
at Port Royal on a flagless boot and the QUEST window that opened was titled
``Sebastian``, with Sebastian's voice and Sebastian's Prison Exile Island
line, while the target panel beside it read ``Columbus`` (attended round
GT-102, notes_to_chief/20260829_0018_KA3A-GT122-PASS-GT102-PARTIAL-GT104-
BLOCKED-mobs-answer-as-npc.md section 2).

The cause is in this tree, one frame earlier than the conversation:
``make_v98_conversation_face_state`` (``current/pf_login_game_server_v141.py``
1088-1096) resolves each actor through the FROZEN table
``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS``, whose row for placement 1 is
``(1, 2, ..., 'M010_001_000_N', 'Sebastian')``.  It then ships that row's
second field - a **Mob-Set number**, not a MOBS id - as the NPCAttr template,
ships Sebastian's avatar basename with it, and drops the row's name field
entirely.  So every click re-tags actor 0x2002 as MOBS 2 (Sebastian, Warden)
after the login census correctly told the client it was MOBS 156 (Columbus).

THIS TEST DOES NOT ASSERT THAT THE BUG IS RIGHT.  It pins the contradiction
so that it cannot be re-derived from scratch a third time, and so that the
day the frozen file's owner lands the one-line fix, exactly one test fails
and its message says what to do.  ``current/pf_login_game_server_v141.py`` is
a frozen artifact this lane does not write to (``AGENTS.md``: it "must be
clean"; ``legacy_bridge``'s own docstring: "frozen V141 serializers"), so the
fix is a CORE-REQUEST, filed with this round:
``notes_to_chief/20260829_0145_LANE-A-CORE-REQUEST-face-frame-uses-the-stale-identity-map.md``

WHAT THE FIX IS, IN ONE LINE, SO THIS FILE CARRIES IT TOO:
    at v141:1094-1096, resolve the row's Mob-Set number through
    ``world_port_royal_identity.resolve()`` and send
    ``identity.mobs_n_id`` / ``identity.outfit`` / ``basic_name=identity.name``
    - the exact call ``world_population._entry`` already makes (that module's
    lines 376-417), never the Mob-Set number.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_port_royal_identity
from pirateforce_foundation.legacy_bridge import load_legacy

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# The placement the owner clicked.  0x2000 + index + 1 is this project's one
# actor-identity formula (population.py), so index 1 is actor 0x2002.
COLUMBUS_PLACEMENT_INDEX = 1
COLUMBUS_ACTOR_IDENTITY = 0x2000 + COLUMBUS_PLACEMENT_INDEX + 1
COLUMBUS_MOBS_N_ID = 156
SEBASTIAN_MOBS_N_ID = 2


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


class FaceFrameContradictsTheCensusTests(unittest.TestCase):
    """The two frames the client receives for actor 0x2002 disagree.

    These assertions read the BYTES the face-frame builder produces, not the
    table it reads.  An earlier version of this file read the table instead,
    and pf-adversary proved the difference by applying the prescribed fix:
    the tests stayed green while the wire changed.  A detector that cannot
    see the thing it detects is worse than no detector, because it is quoted
    as one.
    """

    def setUp(self):
        self.legacy = _legacy()
        # Two placements, one of them the one the owner clicked.  Both must
        # exist in the frozen table or the builder raises.
        face, idx = self.legacy.make_v98_conversation_face_state(
            (0, COLUMBUS_PLACEMENT_INDEX), COLUMBUS_ACTOR_IDENTITY,
            100.0, 200.0,
        )
        self.assertEqual(idx, COLUMBUS_PLACEMENT_INDEX)
        _pc, self.frame = face

    def _attr(self, template_id, preset, name=""):
        return self.legacy.make_npc_attr(
            template_id, COLUMBUS_ACTOR_IDENTITY, 1, 0, preset,
            basic_name=name,
        )

    def test_the_frame_carries_sebastians_identity_for_columbus_actor(self):
        """TODAY's wire, read from the frame itself.

        When the CORE-REQUEST in this module's docstring lands, this test
        FAILS - that is the success signal.  Delete this method then; the
        one below it becomes the permanent assertion.
        """
        self.assertIn(
            self._attr(SEBASTIAN_MOBS_N_ID, "M010_001_000_N"), self.frame,
            "the face frame no longer ships MOBS 2 for actor 0x2002 - if "
            "this fails, the v141 face-frame fix has landed: delete this "
            "method, keep test_the_fixed_face_frame_ships_the_census_"
            "identity, and strike the CORE-REQUEST letter as done",
        )

    # THERE IS DELIBERATELY NO SECOND TEST HERE ASSERTING THE FIXED FRAME.
    # An earlier version of this file carried one that called skipTest while
    # the defect stands.  That is an UNPINNED SKIP, and this repository pins
    # every skip by module in docs/PYTEST_SKIP_PINS.json precisely so a real
    # test cannot drift into the skip pile unnoticed - the Windows gate's
    # skip_census step went red on it and the automerge workflow closed the
    # pull request.  A skipped check is not a passed check, so the check that
    # matters lives in the method above, which FAILS when the fix lands and
    # says so in its message.  The identity the fixed frame must carry is
    # asserted, without any frame, by the method below.

    def test_the_census_side_resolves_the_same_row_to_columbus(self):
        """The half of the contradiction that is already correct.

        Asserts the resolver only, deliberately: the frame side is asserted
        once, by the method above, so that the fix produces EXACTLY ONE red
        with a message that explains it.  A second red saying something
        subtly different is how a green-again suite gets misread.
        """
        row = {
            r[0]: r for r in self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        }[COLUMBUS_PLACEMENT_INDEX]
        identity = world_port_royal_identity.resolve(row[1])
        self.assertEqual(identity.mobs_n_id, COLUMBUS_MOBS_N_ID)
        self.assertEqual(identity.name, "Columbus")
        self.assertEqual(identity.outfit, "M055_000_000_N")

    def test_the_frozen_builder_drops_the_name_field(self):
        """Why the name line is at risk after a click, over the source text.

        ``make_npc_attr`` sets BasicAttr bit 0x0001 only when ``basic_name``
        is truthy, and the face-frame call site passes none - so the field is
        ABSENT, not empty.  Whether the client then clears or retains the
        label it already has is UNMEASURED here, and the attended note's
        "labels vanish after moving" finding carries its own hypothesis tag;
        this test claims only what it reads.

        Matched on the call-site string, which occurs exactly once in the
        frozen file, rather than on a line window: an absolute offset into a
        7,000-line file fires a false red for any edit above it.
        """
        source = LEGACY_PATH.read_text(encoding="utf-8")
        call = "make_npc_attr(template_id, aid, 1, 0, preset)"
        self.assertEqual(
            source.count(call), 1,
            "the face-frame call site moved or multiplied; re-read the "
            "builder before trusting anything else in this file",
        )
        self.assertNotIn(
            self._attr(SEBASTIAN_MOBS_N_ID, "M010_001_000_N", name="Sebastian"),
            self.frame,
            "a name-bearing attr would mean the builder started passing "
            "basic_name, which is half the CORE-REQUEST",
        )


if __name__ == "__main__":
    unittest.main()
