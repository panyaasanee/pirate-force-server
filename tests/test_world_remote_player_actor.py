"""world_remote_player_actor: the always-on actor_type 2 (CNetActor)
composer for a real second player, promoted out of HYP-PF-025's probe.

WHAT THESE TESTS PROVE, AND WHAT THEY DO NOT.  They prove the encoder
composes a real, well-formed ``actor_type 2`` actor entry -- decoded back by
``remote_player_hypothesis``'s own INDEPENDENT walker, not this module's own
composer, so a symmetrical bug cannot hide -- from a row read straight out
of the shared ``world_scene_registry``, that a viewer never receives an
entry for themselves, and that every refusal in the ladder is reachable by
name (the trap-test discipline ``test_remote_player_hypothesis.py`` already
uses: a validator that cannot be made to fail is a printout, not a
validator).  They do NOT prove anything renders on a real client -- that
question is exactly as open here as it is for the probe this module was
promoted from.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import remote_player_hypothesis as rph  # noqa: E402
from pirateforce_foundation import world_scene_registry as wsr  # noqa: E402
from pirateforce_foundation import world_remote_player_actor as wrpa  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

_LEGACY = None


def legacy():
    global _LEGACY
    if _LEGACY is None:
        _LEGACY = load_legacy(LEGACY_PATH)
    return _LEGACY


ALICE = 0x10000001
BOB = 0x10000002
CAROL = 0x10000003
PORT_ROYAL_SCENE_ID = 1
PORT_ROYAL_FOLDER = "bg0001"


def alice() -> wsr.PlayerVital:
    return wsr.PlayerVital(ALICE, "Alice", 100, 100, (10.0, 20.0, 30.0))


def bob() -> wsr.PlayerVital:
    return wsr.PlayerVital(BOB, "Bob", 55, 100, (40.0, 50.0, 60.0))


class ProductionAllowedIsHonest(unittest.TestCase):

    def test_the_module_declares_itself_production_allowed(self):
        # Not a probe: no scenario, no wire-unlock token, no flag anywhere
        # in this module's own import path.
        self.assertIs(wrpa.production_allowed, True)

    def test_it_imports_no_scenario_or_unlock_machinery_from_the_probe(self):
        # The whole point of "promoted, not copied": this module must not be
        # reachable through remote_player_hypothesis's wire-unlock gate,
        # because a lock this module cannot open would make it a probe with
        # extra steps.
        self.assertFalse(hasattr(wrpa, "require_remote_player_wire_unlock"))
        self.assertFalse(hasattr(wrpa, "remote_player_wire_unlock"))


class TheEncodedBytesAreARealActorTypeTwoEntry(unittest.TestCase):
    """Decoded by the PROBE's own independent walker -- not this module's
    composer -- so a bug shared between "compose" and "check my own work"
    cannot hide."""

    def test_the_entry_round_trips_through_the_independent_walker(self):
        entry = wrpa.encode_live_player_actor_entry(
            legacy(), alice(), PORT_ROYAL_SCENE_ID)
        pc, frame = legacy().make_runtime_remote_actors([entry])
        decoded = rph.decode_remote_player_actor_entry_frame(pc)
        self.assertEqual(decoded["actor_type"], rph.REMOTE_PLAYER_ACTOR_TYPE)
        self.assertEqual(decoded["identity"], ALICE)
        actor = decoded["attrs"][rph.ACTOR_ATTR_ID]
        self.assertEqual(actor["basic_mask"], rph.BASIC_MASK_PROBE)
        self.assertEqual(actor["fields"][rph.BASIC_BIT_NAME], "Alice")
        self.assertEqual(actor["fields"][rph.BASIC_BIT_CURRENT_HP], 100)
        self.assertEqual(actor["fields"][rph.BASIC_BIT_MAX_HP], 100)
        self.assertEqual(actor["actor_mask"], rph.ACTOR_ATTR_MASK_PROBE)
        self.assertEqual(actor["extra_group"], rph.ACTOR_ATTR_EXTRA_GROUP_VALUE)
        movement = decoded["attrs"][rph.MOVEMENT_ATTR_ID]
        self.assertEqual(movement["mask"], rph.MOVEMENT_MASK_FULL)
        self.assertEqual(movement["position"], (10.0, 20.0, 30.0))

    def test_a_wounded_players_hp_is_the_wire_hp_not_the_ceiling(self):
        entry = wrpa.encode_live_player_actor_entry(
            legacy(), bob(), PORT_ROYAL_SCENE_ID)
        pc, _frame = legacy().make_runtime_remote_actors([entry])
        decoded = rph.decode_remote_player_actor_entry_frame(pc)
        actor = decoded["attrs"][rph.ACTOR_ATTR_ID]
        self.assertEqual(actor["fields"][rph.BASIC_BIT_CURRENT_HP], 55)
        self.assertEqual(actor["fields"][rph.BASIC_BIT_MAX_HP], 100)

    def test_never_the_death_timer_bit(self):
        """The independent walker itself refuses this bit outright (it is
        the death lane's field, HYP-PF-023's) -- this test pins that this
        encoder never sets it, mutant-catching if anyone ever adds it."""
        entry = wrpa.encode_live_player_actor_entry(
            legacy(), alice(), PORT_ROYAL_SCENE_ID)
        pc, _frame = legacy().make_runtime_remote_actors([entry])
        decoded = rph.decode_remote_player_actor_entry_frame(pc)
        actor = decoded["attrs"][rph.ACTOR_ATTR_ID]
        self.assertEqual(
            actor["basic_mask"] & rph.BASIC_BIT_DEATH_TIMER_FORBIDDEN, 0)

    def test_the_cross_check_against_make_npc_attr_really_runs(self):
        """The same free-oracle cross-check the probe runs on itself, proven
        LIVE rather than merely present: a ``legacy`` whose ``make_npc_attr``
        disagrees with this encoder's own construction must refuse, by name,
        rather than let the two silently drift -- a decoder built from the
        SAME wrong offsets would happily decode the wrong bytes, so "it
        decodes" alone is not evidence the prefix is right."""
        class DisagreeingLegacy:
            def __getattr__(self, attr):
                return getattr(legacy(), attr)

            def make_npc_attr(self, *args, **kwargs):
                real = legacy().make_npc_attr(*args, **kwargs)
                # Flip one byte inside the span this cross-check compares
                # (well before the NPC-only tail) so the two disagree.
                return bytes([real[0] ^ 0xFF]) + real[1:]

        with self.assertRaises(wrpa.RemotePlayerActorRefusal) as failure:
            wrpa.encode_live_player_actor_attr(
                DisagreeingLegacy(), alice(), PORT_ROYAL_SCENE_ID)
        self.assertIn("basic_prefix_does_not_reproduce_make_npc_attr",
                     str(failure.exception))


class TheHpFloorIsEnforced(unittest.TestCase):

    def test_the_row_type_itself_refuses_zero_hp(self):
        with self.assertRaises(ValueError):
            wsr.PlayerVital(ALICE, "Alice", 0, 100, (0.0, 0.0, 0.0))

    def test_the_encoder_refuses_a_hand_built_zero_hp_row(self):
        """Belt AND braces: even if a caller somehow got a zero-hp row past
        the dataclass (a monkeypatch, a different constructor path in a
        future refactor), the encoder's own floor check must still refuse
        it by name rather than trust the type."""
        row = alice()
        object.__setattr__(row, "current_hp", 0)
        with self.assertRaises(wrpa.RemotePlayerActorRefusal) as failure:
            wrpa.encode_live_player_actor_attr(
                legacy(), row, PORT_ROYAL_SCENE_ID)
        self.assertIn("hp_zero_would_cross_into_the_death_chain",
                     str(failure.exception))


class TheEntryRejectsWrongShapes(unittest.TestCase):

    def test_not_a_player_vital_row_is_refused_by_name(self):
        with self.assertRaises(wrpa.RemotePlayerActorRefusal) as failure:
            wrpa.encode_live_player_actor_attr(
                legacy(), {"name": "Eve"}, PORT_ROYAL_SCENE_ID)
        self.assertIn("not_a_player_vital_row", str(failure.exception))

    def test_movement_attr_also_refuses_a_wrong_shape(self):
        with self.assertRaises(wrpa.RemotePlayerActorRefusal):
            wrpa.encode_live_player_movement_attr(legacy(), object())


class ComposingTheOtherPlayersFrame(unittest.TestCase):
    """The read side: the world registry -> one snapshot frame naming every
    OTHER player, viewer's own row always excluded."""

    def setUp(self):
        self.registry = wsr.WorldSceneRegistry()

    def _note(self, player: wsr.PlayerVital):
        outcome = self.registry.note_player(
            PORT_ROYAL_FOLDER, player.actor_identity, player.name,
            player.current_hp, player.max_hp, player.position)
        self.assertTrue(outcome.noted, outcome.reason)

    def test_an_empty_registry_answers_the_empty_frame(self):
        result = wrpa.compose_other_live_players_frame(
            legacy(), PORT_ROYAL_SCENE_ID, ALICE, registry=self.registry)
        self.assertEqual(result.actor_count, 0)
        self.assertEqual(result.pc, b"")
        self.assertEqual(result.frame, b"")
        self.assertEqual(result.identities, ())

    def test_the_viewer_never_receives_their_own_entry(self):
        self._note(alice())
        result = wrpa.compose_other_live_players_frame(
            legacy(), PORT_ROYAL_SCENE_ID, ALICE, registry=self.registry)
        self.assertEqual(result.actor_count, 0)
        self.assertNotIn(ALICE, result.identities)

    def test_a_second_player_in_the_same_scene_is_composed_for_the_first(self):
        self._note(alice())
        self._note(bob())
        result = wrpa.compose_other_live_players_frame(
            legacy(), PORT_ROYAL_SCENE_ID, ALICE, registry=self.registry)
        self.assertEqual(result.actor_count, 1)
        self.assertEqual(result.identities, (BOB,))
        decoded = rph.decode_remote_player_actor_entry_frame(result.pc)
        self.assertEqual(decoded["identity"], BOB)
        self.assertEqual(
            decoded["attrs"][rph.ACTOR_ATTR_ID]["fields"][rph.BASIC_BIT_NAME],
            "Bob")

    def test_symmetry_the_second_player_is_composed_the_first(self):
        """The shared-world property this feature exists to demonstrate: BOTH
        directions see the OTHER one, from the exact same registry rows --
        not one session's private idea of who else is there."""
        self._note(alice())
        self._note(bob())
        seen_by_alice = wrpa.compose_other_live_players_frame(
            legacy(), PORT_ROYAL_SCENE_ID, ALICE, registry=self.registry)
        seen_by_bob = wrpa.compose_other_live_players_frame(
            legacy(), PORT_ROYAL_SCENE_ID, BOB, registry=self.registry)
        self.assertEqual(seen_by_alice.identities, (BOB,))
        self.assertEqual(seen_by_bob.identities, (ALICE,))

    def test_three_players_two_others_each(self):
        self._note(alice())
        self._note(bob())
        self._note(wsr.PlayerVital(CAROL, "Carol", 80, 80, (1.0, 1.0, 1.0)))
        result = wrpa.compose_other_live_players_frame(
            legacy(), PORT_ROYAL_SCENE_ID, ALICE, registry=self.registry)
        self.assertEqual(result.actor_count, 2)
        self.assertEqual(set(result.identities), {BOB, CAROL})

    def test_a_scene_this_project_has_no_folder_for_answers_empty(self):
        result = wrpa.compose_other_live_players_frame(
            legacy(), 999999, ALICE, registry=self.registry)
        self.assertEqual(result.actor_count, 0)
        self.assertEqual(result.scene_id, 999999)

    def test_a_malformed_scene_id_refuses_rather_than_raises(self):
        result = wrpa.compose_other_live_players_frame(
            legacy(), "not-an-int", ALICE, registry=self.registry)
        self.assertEqual(result.actor_count, 0)

    def test_a_malformed_viewer_identity_refuses_rather_than_raises(self):
        self._note(alice())
        result = wrpa.compose_other_live_players_frame(
            legacy(), PORT_ROYAL_SCENE_ID, "not-an-int", registry=self.registry)
        self.assertEqual(result.actor_count, 0)

    def test_a_registry_that_raises_costs_the_caller_nothing(self):
        class Hostile:
            def remembered_players(self, scene):
                raise RuntimeError("boom")
        result = wrpa.compose_other_live_players_frame(
            legacy(), PORT_ROYAL_SCENE_ID, ALICE, registry=Hostile())
        self.assertEqual(result.actor_count, 0)

    def test_the_reader_re_reads_the_registry_every_call(self):
        """No caching: a player who leaves between two calls is correctly
        absent from the second one -- the same "seeded from, never replaced
        by" discipline the module docstring names for the monster book."""
        self._note(alice())
        self._note(bob())
        first = wrpa.compose_other_live_players_frame(
            legacy(), PORT_ROYAL_SCENE_ID, ALICE, registry=self.registry)
        self.assertEqual(first.actor_count, 1)
        self.registry.forget_player(PORT_ROYAL_FOLDER, BOB)
        second = wrpa.compose_other_live_players_frame(
            legacy(), PORT_ROYAL_SCENE_ID, ALICE, registry=self.registry)
        self.assertEqual(second.actor_count, 0)

    def test_describe_line_is_ascii_and_names_the_scene(self):
        self._note(alice())
        self._note(bob())
        result = wrpa.compose_other_live_players_frame(
            legacy(), PORT_ROYAL_SCENE_ID, ALICE, registry=self.registry)
        line = wrpa.describe_live_players_frame(result)
        line.encode("ascii")
        self.assertIn("other_players=1", line)

    def test_describe_line_never_raises_on_a_shape_it_did_not_expect(self):
        line = wrpa.describe_live_players_frame(object())
        line.encode("ascii")


class TheSceneIdConvenienceDoors(unittest.TestCase):
    """register_player_presence/clear_player_presence: the same registry,
    reached by scene id instead of the registry's own folder string."""

    def setUp(self):
        self.registry = wsr.WorldSceneRegistry()

    def test_register_then_compose_sees_it(self):
        outcome = wrpa.register_player_presence(
            PORT_ROYAL_SCENE_ID, ALICE, "Alice", 100, 100,
            (1.0, 2.0, 3.0), registry=self.registry)
        self.assertTrue(outcome.noted, outcome.reason)
        result = wrpa.compose_other_live_players_frame(
            legacy(), PORT_ROYAL_SCENE_ID, BOB, registry=self.registry)
        self.assertEqual(result.identities, (ALICE,))

    def test_clear_then_compose_no_longer_sees_it(self):
        wrpa.register_player_presence(
            PORT_ROYAL_SCENE_ID, ALICE, "Alice", 100, 100,
            (0.0, 0.0, 0.0), registry=self.registry)
        self.assertTrue(
            wrpa.clear_player_presence(
                PORT_ROYAL_SCENE_ID, ALICE, registry=self.registry))
        result = wrpa.compose_other_live_players_frame(
            legacy(), PORT_ROYAL_SCENE_ID, BOB, registry=self.registry)
        self.assertEqual(result.actor_count, 0)

    def test_an_unaddressed_scene_id_refuses_the_write(self):
        outcome = wrpa.register_player_presence(
            999999, ALICE, "Alice", 100, 100, (0.0, 0.0, 0.0),
            registry=self.registry)
        self.assertFalse(outcome.noted)

    def test_an_unaddressed_scene_id_refuses_the_clear(self):
        self.assertFalse(
            wrpa.clear_player_presence(999999, ALICE, registry=self.registry))


class TheWiringAsk(unittest.TestCase):
    """Same discipline test_world_scene_registry.py's own TheWiringAsk uses
    for WORLD_REGISTRY_SEED_WIRING: the ask's own anchors must really be in
    runtime.py today, or the letter is pointing at a line that does not
    exist."""

    def test_the_pasteable_ask_names_the_functions_it_asks_for(self):
        text = wrpa.PLAYER_PRESENCE_WIRING
        self.assertIn("register_player_presence", text)
        self.assertIn("clear_player_presence", text)
        self.assertIn("compose_other_live_players_frame", text)
        self.assertIn("from . import world_remote_player_actor", text)
        text.encode("ascii")

    def test_every_runtime_anchor_the_ask_names_is_really_in_runtime_today(self):
        runtime = (ROOT / "src" / "pirateforce_foundation" / "runtime.py"
                   ).read_text(encoding="utf-8")
        for anchor in (
                "lane_hooks.register_live_session(",
                "self.last_target_pos = (x, y, z, heading)",
                "def _vital_walk_promote_target_pos",
        ):
            with self.subTest(anchor=anchor[:40]):
                self.assertIn(anchor, runtime)


if __name__ == "__main__":
    unittest.main()
