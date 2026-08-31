"""PLAYER-HOSTILE-PAIRING-001 -- the player's half of the pairing, offline.

Proves the pure composer directly against the real frozen V141 serializer
(no dispatch, no database, no socket): a character at the production
default spawn (scene 1, seq 0 -- ``app.py``'s own ``default`` Position,
read here as a literal, not imported, since ``app.py`` is the chief's file)
gets a StartGame response with the player's PLAYER_PAIR_FACTION spliced in,
byte-identical in shape to what the already-PASSED ``GT-032`` probe sends
for its player half; a character the frozen serializer does not accept
(any other scene/seq) gets the untouched production bytes back, unchanged,
with a named refusal event -- never a half-composed or fabricated frame.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.model import Character, Position  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import player_hostile_pairing as php  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


def _character(scene_id: int, scene_seq: int, *, identity_lo=0x99999999,
               identity_hi=0) -> Character:
    return Character(
        id=1, account_id=1, selector=0, name="Pirate",
        actor_wire=b"", avatar_wire=b"",
        identity_lo=identity_lo, identity_hi=identity_hi,
        position=Position(scene_id, scene_seq, 0.0, 0.0, 0.0, 0.0),
    )


class PlayerHostilePairingTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)

    def _production_start_game(self, character):
        return self.projector.start_game(character, backpack=None)

    def test_default_spawn_scene_gets_the_faction_spliced_in(self):
        # scene 1, seq 0 is app.py's own literal default spawn Position --
        # every character created today starts exactly here.
        character = _character(1, 0)
        pc, frame = self._production_start_game(character)
        out_pc, out_frame, sent, event = (
            php.compose_start_game_with_player_pairing(
                self.projector, character, None, pc, frame,
            )
        )
        self.assertTrue(sent, event)
        self.assertEqual(event, php.SENT_EVENT)
        self.assertEqual(
            len(out_pc), len(pc) + field_mobs.FACTION_SPLICE_BYTES,
        )
        self.assertEqual(
            len(out_frame), len(frame) + field_mobs.FACTION_SPLICE_BYTES,
        )
        # Byte-identical to calling the frozen serializer directly with the
        # same faction -- this module adds no bytes of its own.
        direct_pc, direct_frame = self.projector.start_game(
            character, basic_faction=php.PLAYER_PAIR_FACTION, backpack=None,
        )
        self.assertEqual(out_pc, direct_pc)
        self.assertEqual(out_frame, direct_frame)

    def test_scene_2_seq_0_also_accepted(self):
        # make_actor_attr_with_basic_faction's own guard: scene_id in (1, 2).
        character = _character(2, 0)
        pc, frame = self._production_start_game(character)
        _out_pc, _out_frame, sent, event = (
            php.compose_start_game_with_player_pairing(
                self.projector, character, None, pc, frame,
            )
        )
        self.assertTrue(sent, event)

    def test_any_identity_is_accepted_not_just_one_pinned_smoke_character(self):
        # Unlike runtime.py's _npc_hostile_start_game_response, this
        # composer carries no identity pin -- that is the whole point of
        # generalizing it off the one HYP-PF-027 smoke identity.
        for lo, hi in ((0x10010001, 0), (0x20000001, 0), (0xABCDEF01, 7)):
            character = _character(1, 0, identity_lo=lo, identity_hi=hi)
            pc, frame = self._production_start_game(character)
            _out_pc, _out_frame, sent, event = (
                php.compose_start_game_with_player_pairing(
                    self.projector, character, None, pc, frame,
                )
            )
            self.assertTrue(sent, f"identity {lo:#x}/{hi:#x}: {event}")

    def test_unaccepted_scene_fails_closed_to_untouched_production_bytes(self):
        # Any scene ``world_faction_admission`` does not admit must come
        # back byte-identical to production, never a fabricated or
        # half-composed frame.  MOVED this round from scene 7 (Voodoo
        # Island, which world_faction_admission now admits since its
        # registry row opened this round) to scene 9 (Death City Sea),
        # still one of the three doors this lane has not yet opened.
        character = _character(9, 0)
        pc, frame = self._production_start_game(character)
        out_pc, out_frame, sent, event = (
            php.compose_start_game_with_player_pairing(
                self.projector, character, None, pc, frame,
            )
        )
        self.assertFalse(sent)
        self.assertTrue(event.startswith(php.REFUSAL_COMPOSE), event)
        self.assertEqual(out_pc, pc)
        self.assertEqual(out_frame, frame)

    def test_nonzero_scene_seq_fails_closed(self):
        # scene 1 is accepted, but scene_seq must be exactly 0 -- a
        # character who has moved within the accepted scene (once travel
        # ever changes scene_seq; today's checkpoint path never does) must
        # not silently get a fabricated pairing.
        character = _character(1, 7)
        pc, frame = self._production_start_game(character)
        out_pc, out_frame, sent, event = (
            php.compose_start_game_with_player_pairing(
                self.projector, character, None, pc, frame,
            )
        )
        self.assertFalse(sent)
        self.assertTrue(event.startswith(php.REFUSAL_COMPOSE), event)
        self.assertEqual(out_pc, pc)
        self.assertEqual(out_frame, frame)

    def test_none_selected_fails_closed_instead_of_crashing(self):
        # A caller passing an unselected character (e.g. a wiring mistake,
        # or a connection state this module has never seen) must not raise
        # out of a function whose whole contract is "never crash the
        # connection thread, fail closed instead" -- pf-adversary
        # self-review target.
        pc, frame = b"AA", b"BB"
        out_pc, out_frame, sent, event = (
            php.compose_start_game_with_player_pairing(
                self.projector, None, None, pc, frame,
            )
        )
        self.assertFalse(sent)
        self.assertTrue(event.startswith(php.REFUSAL_COMPOSE), event)
        self.assertEqual(out_pc, pc)
        self.assertEqual(out_frame, frame)

    def test_describe_pairing_attempt_is_a_stable_greppable_line(self):
        line_sent = php.describe_pairing_attempt(True, php.SENT_EVENT)
        line_refused = php.describe_pairing_attempt(
            False, php.REFUSAL_LENGTH_DRIFT,
        )
        self.assertIn("PLAYER_HOSTILE_PAIRING_ATTEMPT", line_sent)
        self.assertIn("sent=True", line_sent)
        self.assertIn("PLAYER_HOSTILE_PAIRING_ATTEMPT", line_refused)
        self.assertIn("sent=False", line_refused)
        self.assertIn(php.REFUSAL_LENGTH_DRIFT, line_refused)
        # cp874-encodable: everything this project ever prints must be.
        line_sent.encode("cp874")
        line_refused.encode("cp874")

    def test_faction_constant_is_the_same_object_field_mobs_uses(self):
        # Single source of truth: the player and monster faction constants
        # must never be able to drift apart in two different modules.
        self.assertEqual(php.PLAYER_PAIR_FACTION, field_mobs.PLAYER_PAIR_FACTION)

    def test_backpack_none_uses_the_same_default_backpack_production_does(self):
        # backpack=None must resolve identically on both sides of the
        # comparison (this module does not invent a different default).
        character = _character(1, 0)
        pc, frame = self.projector.start_game(character, backpack=None)
        out_pc, _out_frame, sent, _event = (
            php.compose_start_game_with_player_pairing(
                self.projector, character, None, pc, frame,
            )
        )
        self.assertTrue(sent)
        self.assertTrue(out_pc.startswith(pc[:1]))


if __name__ == "__main__":
    unittest.main()
