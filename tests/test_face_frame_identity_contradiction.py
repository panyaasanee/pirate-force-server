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

    Both assertions below describe TODAY.  The first is the defect; the day
    the CORE-REQUEST in this module's docstring lands, it fails and this
    class is what tells the next reader that the failure is the good news.
    """

    def setUp(self):
        self.legacy = _legacy()

    def _npc_attr_template_in_face_frame(self) -> int:
        """The MOBS/template u16 the face frame ships for actor 0x2002.

        Read from the frozen builder's own inputs rather than by parsing the
        frame: the builder passes the row's field 1 straight into
        ``make_npc_attr``'s first parameter (v141:1094-1096), and that
        parameter is documented there as "the MOBS/template u16 at +0x78".
        Parsing the bytes would test the serializer, which V97 already pins;
        what is at stake here is WHICH NUMBER is handed to it.
        """
        row = {
            r[0]: r for r in self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        }[COLUMBUS_PLACEMENT_INDEX]
        return row[1]

    def test_face_frame_ships_the_set_number_while_census_ships_the_mobs_id(self):
        face_value = self._npc_attr_template_in_face_frame()
        census_value = world_port_royal_identity.resolve(face_value).mobs_n_id
        self.assertNotEqual(
            face_value, census_value,
            "PLACEMENT 1's identity now agrees across both frames - if this "
            "test fails, the v141 face-frame CORE-REQUEST has landed: delete "
            "this class and turn the assertion in "
            "test_the_fixed_face_frame_must_ship_the_census_identity into the "
            "permanent one.",
        )

    def test_the_fixed_face_frame_must_ship_the_census_identity(self):
        """The invariant the fix has to satisfy, written before the fix.

        This one is not a description of today - it is the acceptance test
        for the CORE-REQUEST, expressed over the resolver both paths will
        share.  It passes now because it asserts the resolver, and it is
        what the fixed call site must reproduce on the wire.
        """
        identity = world_port_royal_identity.resolve(
            self._npc_attr_template_in_face_frame()
        )
        self.assertEqual(identity.mobs_n_id, COLUMBUS_MOBS_N_ID)
        self.assertEqual(identity.outfit, "M055_000_000_N")
        self.assertEqual(identity.name, "Columbus")

    def test_the_frozen_builder_drops_the_name_field(self):
        """Why the name line vanishes after a click, in one assertion.

        ``make_npc_attr``'s docstring: BasicAttr bit 0x0001 is the name
        std::wstring the target-panel updater copies into LABEL_NAME.  The
        face-frame builder never passes ``basic_name``, so every click
        re-sends every population actor with an empty name.  Read from the
        frozen source text because the defect is an ARGUMENT THAT IS NOT
        THERE, which no frame can show.
        """
        source = LEGACY_PATH.read_text(encoding="utf-8").splitlines()
        builder = "\n".join(source[1077:1100])
        self.assertIn("make_npc_attr(template_id, aid, 1, 0, preset)", builder,
                      "the face-frame call site moved; re-read v141:1088-1100")
        self.assertNotIn("basic_name", builder)


if __name__ == "__main__":
    unittest.main()
