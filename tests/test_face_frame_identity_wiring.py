"""The face-frame identity fix, driven through the REAL dispatcher.

WHY THIS FILE EXISTS SEPARATELY FROM
``tests/test_face_frame_identity_contradiction.py``.  That file asserts the
BUILDER's bytes; this one asserts what a player's click actually gets back.
The distinction is the whole risk of this fix: ``world_face_frame`` corrects
the frame on the way OUT of ``runtime``'s dispatch rather than at the frozen
builder that composes it, so a unit test of the builder proves nothing about
whether the correction is reached.  A fix that is never reached is
decorative, and a decorative fix that is quoted as landed is worse than an
open bug.

Same harness convention as ``tests/test_columbus_quest_dispatch_wiring.py``:
``runtime.make_state_class`` itself, headless -- no server process, no
socket, no client -- through a full login/create/start-game sequence, then a
TargetPos frame to arm the arrival census, then a real inbound ChooseNPC.

MUTATION-PROOF ON PURPOSE.  Delete the ``rebuild_face_actions`` call from
``runtime.py`` and ``test_the_face_frame_a_click_returns_names_columbus``
fails on the bytes -- it does not merely go quiet, because it asserts the
NPCAttr that must be PRESENT and the one that must be ABSENT, and the frozen
builder supplies the second one.

STILL WIRE-LAYER ONLY.  Nothing here claims the owner sees Columbus's window
or hears Columbus's voice; that is ``GT-102``.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_face_frame
from pirateforce_foundation import world_port_royal_identity
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

COLUMBUS_PLACEMENT_INDEX = 1
COLUMBUS_ACTOR_IDENTITY = 0x2000 + COLUMBUS_PLACEMENT_INDEX + 1
COLUMBUS_MOBS_N_ID = 156
SEBASTIAN_MOBS_N_ID = 2


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _choose_npc_pc(legacy, *actor_ids: int) -> bytes:
    body = b"".join(
        legacy.u16tag(0x12, legacy.CHOOSE_NPC)
        + legacy.u8tag(0x0B, 0)
        + legacy.qwordtag(0x32, actor_id)
        for actor_id in actor_ids
    )
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, len(actor_ids))
        + body
    )


def _target_pos_pc(legacy, xyz=(10.0, 20.0, 30.0), heading=0.0, moving=0,
                   derived=0) -> bytes:
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
        + legacy.u8tag(0x0B, 0)
        + b"".join(legacy.f32tag(value) for value in (*xyz, heading))
        + legacy.u8tag(0x0B, moving)
        + legacy.u8tag(0x0B, derived)
    )


class FaceFrameIdentityWiringTests(unittest.TestCase):
    """Boots through ``runtime.make_state_class`` itself, not a double."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def _real_state(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(state.foundation.account_id)[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        state.dispatch(self.legacy.parse_outer(_target_pos_pc(self.legacy)))
        return state

    def _face_actions(self, actions):
        return [a for a in actions if world_face_frame.is_face_label(a[0])]

    def test_a_real_click_returns_a_face_frame_at_all(self):
        """If this fails, every other assertion here is vacuous."""
        state = self._real_state("tok-face-exists")
        actions = state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, COLUMBUS_ACTOR_IDENTITY)
        ))
        self.assertEqual(
            len(self._face_actions(actions)), 1,
            f"labels were {[a[0] for a in actions]}",
        )

    def test_the_face_frame_a_click_returns_names_columbus(self):
        """THE ONE THAT MATTERS.  Read from the bytes the dispatcher hands
        back, for the actor the owner clicked.

        Both halves are asserted: the identity that must be there, and the
        one that must not.  The frozen builder still composes the second, so
        deleting the rebuild call from ``runtime.py`` fails this loudly
        instead of quietly."""
        state = self._real_state("tok-face-identity")
        actions = state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, COLUMBUS_ACTOR_IDENTITY)
        ))
        frame = self._face_actions(actions)[0][2]

        identity = world_port_royal_identity.resolve(2)
        self.assertEqual(identity.mobs_n_id, COLUMBUS_MOBS_N_ID)
        self.assertIn(
            self.legacy.make_npc_attr(
                identity.mobs_n_id, COLUMBUS_ACTOR_IDENTITY, 1, 0,
                identity.outfit, basic_name=identity.name,
            ),
            frame,
            "the frame a click returns does not carry the census identity - "
            "the rebuild is not being reached on the real dispatch path",
        )
        self.assertNotIn(
            self.legacy.make_npc_attr(
                SEBASTIAN_MOBS_N_ID, COLUMBUS_ACTOR_IDENTITY, 1, 0,
                "M010_001_000_N",
            ),
            frame,
            "the client is still being told actor 0x2002 is MOBS 2 "
            "(Sebastian the Warden) - this is the GT-102 defect on the wire",
        )

    def test_the_dispatcher_records_that_it_resolved_the_identity(self):
        state = self._real_state("tok-face-events")
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, COLUMBUS_ACTOR_IDENTITY)
        ))
        self.assertIn(
            f"face_frame_identity_resolved_p{COLUMBUS_PLACEMENT_INDEX}",
            state.events,
        )
        self.assertFalse(
            [e for e in state.events if e.startswith("face_frame_dropped_")],
            "a real flagless boot dropped a face frame; the census armed a "
            "placement whose identity cannot be shipped",
        )

    def test_the_armed_population_holds_no_unresolvable_placement(self):
        """The production-path premise of the omission rule, asserted rather
        than assumed: ``census_order`` already drops what cannot be shipped,
        so the click frame never has to decide about one."""
        state = self._real_state("tok-face-population")
        self.assertIsNotNone(state.population_indices)
        self.assertEqual(
            world_face_frame.omitted_indices(
                self.legacy, state.population_indices,
            ),
            (),
        )

    def test_a_double_click_rebuilds_every_face_frame_it_returns(self):
        """v141 answers one ChooseNPC per distinct actor in a RuntimeReq, so
        a burst can return more than one face frame.  Rebuilding only the
        first would leave the others naming the wrong person."""
        state = self._real_state("tok-face-burst")
        # NOT "the next index that is not Columbus" - pf-adversary (D5)
        # measured that census_order puts the pinned control set first, so
        # that expression always chose placement 30, the one v141 explicitly
        # REFUSES to answer (`v112_choose_p30_usage1_no_npc_response`).  The
        # test then saw one face frame, passed, and never exercised the
        # multi-frame branch it is named for.  Exclude the two placements the
        # frozen branch treats specially and assert the count exactly.
        refused = {
            self.legacy.V112_MONSTER_INDEX,
            self.legacy.V112_SHOP_TRIGGER_INDEX,
            COLUMBUS_PLACEMENT_INDEX,
        }
        second_index = next(
            idx for idx in state.population_indices if idx not in refused
        )
        actions = state.dispatch(self.legacy.parse_outer(_choose_npc_pc(
            self.legacy, COLUMBUS_ACTOR_IDENTITY, 0x2000 + second_index + 1,
        )))
        faces = self._face_actions(actions)
        self.assertEqual(
            len(faces), 2,
            "a two-actor ChooseNPC returned "
            f"{[a[0] for a in faces]} - the multi-frame branch is untested",
        )
        by_idx = {
            row[0]: row
            for row in self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        }
        for label, _pc, frame, *_rest in faces:
            idx = int(label.rsplit("P", 1)[1])
            aid = 0x2000 + idx + 1
            stale = by_idx[idx][1]
            self.assertNotIn(
                self.legacy.make_npc_attr(stale, aid, 1, 0, by_idx[idx][5]),
                frame,
                f"face frame for placement {idx} still ships its Mob-Set "
                "number as an identity",
            )

    def test_every_actor_in_the_returned_frame_is_one_the_census_shipped(self):
        """The frame must not introduce an actor the client was never told
        about, which is what an unresolvable placement would be."""
        state = self._real_state("tok-face-roster")
        actions = state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, COLUMBUS_ACTOR_IDENTITY)
        ))
        frame = self._face_actions(actions)[0][2]
        # pf-adversary (D4) proved the first version of this test executed
        # ZERO assertions, by construction and permanently: the placements
        # outside the census ARE the unresolvable ones - that is what
        # census_order does - so a `continue` on `identity is None` skipped
        # every one of them.  Assert the roster by COUNT instead, which
        # cannot be skipped: one actor entry per armed placement, no more.
        entries = frame.count(
            self.legacy.u16tag(0x12, self.legacy.NPC_ATTR)
        )
        self.assertEqual(
            entries, len(state.population_indices),
            "the face frame carries a different number of actors than the "
            "census armed",
        )
        self.assertEqual(
            world_face_frame.omitted_indices(
                self.legacy, state.population_indices,
            ),
            (),
            "the gated path armed an unresolvable placement, so the count "
            "check above is not the roster check it claims to be",
        )


class CensusAuthorityGateTests(unittest.TestCase):
    """The rebuild follows the census that is in force - it does not overrule it.

    WHY THIS CLASS EXISTS.  pf-adversary measured (round c5nwjc, D2) that an
    UNGATED rebuild made things worse on every lane boot and on the frozen
    P0/P30/P91 fallback.  Those paths ship the frozen rows' Mob-Set numbers as
    identities at login, so "correcting" the click frame made the two frames
    disagree in the opposite direction, and dropped actor 0x2001 from a frame
    after login had already announced it to the client.

    The rule this pins is therefore NOT "the resolved identity is always
    right".  It is "the click frame must say whatever THIS login said".
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def _state(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(state.foundation.account_id)[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        state.dispatch(self.legacy.parse_outer(_target_pos_pc(self.legacy)))
        return state

    def test_the_flag_starts_false_so_an_unarmed_session_rebuilds_nothing(self):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        self.assertFalse(state_type("tok-unarmed").world_census_identity_resolved)

    def test_the_resolved_census_sets_the_flag(self):
        self.assertTrue(self._state("tok-gate-on").world_census_identity_resolved)

    def test_a_census_that_did_not_resolve_identities_is_left_alone(self):
        """The frozen fallback's frame must survive untouched.

        Asserted on the BYTES: the Mob-Set-numbered NPCAttr the frozen census
        announced at login must still be the one the click frame carries, and
        no face-frame event may be recorded at all.
        """
        state = self._state("tok-gate-off")
        # Exactly what _world_census_frozen_fallback leaves behind.
        state.world_census_identity_resolved = False
        before = len(state.events)
        actions = state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, COLUMBUS_ACTOR_IDENTITY)
        ))
        faces = [a for a in actions if world_face_frame.is_face_label(a[0])]
        self.assertEqual(len(faces), 1)
        row = {
            r[0]: r for r in self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        }[COLUMBUS_PLACEMENT_INDEX]
        self.assertIn(
            self.legacy.make_npc_attr(
                row[1], COLUMBUS_ACTOR_IDENTITY, 1, 0, row[5],
            ),
            faces[0][2],
            "an ungated rebuild corrected a frame whose login census had not "
            "been corrected - the two frames now disagree the other way",
        )
        self.assertFalse(
            [e for e in state.events[before:] if e.startswith("face_frame_")],
            "the rebuild ran on a census it does not have authority over",
        )


if __name__ == "__main__":
    unittest.main()
