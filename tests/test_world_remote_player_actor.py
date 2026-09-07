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

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import remote_player_hypothesis as rph  # noqa: E402
from pirateforce_foundation import world_scene_registry as wsr  # noqa: E402
from pirateforce_foundation import world_scene_entry as wse  # noqa: E402
from pirateforce_foundation import model  # noqa: E402
from pirateforce_foundation import player_wire  # noqa: E402
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
        for door in ("register_presence_for_login",
                     "register_presence_for_character",
                     "clear_player_presence",
                     "compose_other_live_players_frame"):
            with self.subTest(door=door):
                self.assertIn(door, text)
                self.assertTrue(callable(getattr(wrpa, door)))
        self.assertIn("from . import world_remote_player_actor", text)
        text.encode("ascii")

    def test_every_runtime_anchor_the_ask_names_is_really_in_runtime_today(self):
        runtime = (ROOT / "src" / "pirateforce_foundation" / "runtime.py"
                   ).read_text(encoding="utf-8")
        for anchor in (
                # call site (1), revision 2: AFTER the entry is resolved and
                # after the override resync, before the GM-state block.
                "entry = world_scene_entry.resolve_entry(",
                "gm_login_scene_override_selected_position_",
                "is_gm = is_gm_account(self.token)",
                # call site (2)
                "self.last_target_pos = (x, y, z, heading)",
                "def _vital_walk_promote_target_pos",
        ):
            with self.subTest(anchor=anchor[:40]):
                self.assertIn(anchor, runtime)

    def test_the_ask_no_longer_points_at_the_anchor_that_measured_wrong(self):
        """Revision 1 told chief to paste call site (1) right after
        ``lane_hooks.register_live_session(...)``, which runs BEFORE
        ``resolve_entry``.  pf-adversary round q6a8oa (D1) measured what that
        does on the GM login-scene-override path: a ghost row in the scene
        the player came from, and nobody visible in the scene the player is
        standing in.  This pins that the ask does not walk back to it."""
        text = wrpa.PLAYER_PRESENCE_WIRING
        after = text.split("WHY NOT AT", 1)
        self.assertEqual(len(after), 2,
                         "the ask must keep saying why that anchor is wrong")
        # The old anchor may only appear inside that explanation, never as
        # an instruction.
        instructions = after[0]
        self.assertNotIn("lane_hooks.register_live_session", instructions)

    def test_the_ask_does_not_claim_the_pastes_read_no_fields(self):
        """D4: revision 1 said "none of these pastes reads a field" while
        call site (3) in the same string reads ``.id``, and said all three
        doors read the HP pair when only one of them does."""
        text = wrpa.PLAYER_PRESENCE_WIRING
        self.assertIn(".id", text)
        self.assertNotIn("none of these pastes reads a field", text)

    def test_the_ask_says_how_much_of_walking_call_site_two_covers(self):
        """D6: call site (2) sits after a line the ordinary TargetPos frame
        never reaches -- ``_vital_walk_promote_target_pos`` returns
        ``v141_reads_this_frame_itself`` first, by design, so one field never
        has two authors.  An ask that did not say so was overselling."""
        self.assertIn("v141_reads_this_frame_itself",
                      wrpa.PLAYER_PRESENCE_WIRING)
        runtime = (ROOT / "src" / "pirateforce_foundation" / "runtime.py"
                   ).read_text(encoding="utf-8")
        self.assertIn('return "v141_reads_this_frame_itself"', runtime)


_MIRROR_THE_PAIR = object()


def _character(*, identity=7001, name="Panya", scene_id=1,
               xyz=(10.0, 20.0, 30.0), hp=None, hp_max=None,
               level=_MIRROR_THE_PAIR):
    """A real ``model.Character``, not a stub: the door under test reads the
    same row ``runtime.py`` holds, so a test that invented its own shape
    could pass while the paste site failed.

    ``level`` defaults to MIRRORING the pair, because that is the only shape
    a real login produces: ``PANYA-DECISION 20260901_1059`` makes the three
    login vitals all-or-none, and ``legacy_bridge.start_game`` reads all
    three before it sends any of them.  Pass ``level=`` explicitly to build
    the partial rows that rule forbids."""
    if level is _MIRROR_THE_PAIR:
        level = 1 if (hp is not None or hp_max is not None) else None
    return model.Character(
        identity, 1, 0, name, b"", b"", 0, 0,
        model.Position(scene_id, 0, xyz[0], xyz[1], xyz[2]),
        level=level, hp_current=hp, hp_max=hp_max,
    )


class HpPairForACharacterRow(unittest.TestCase):
    """The read that used to be an open question in PLAYER_PRESENCE_WIRING.

    Every refusal below is reachable BY NAME.  A pair validator that cannot
    be made to fail is a printout, not a validator -- the same discipline the
    rest of this file already applies to the encoder.
    """

    def test_a_row_that_carries_no_pair_answers_the_login_constants(self):
        pair = wrpa.hp_pair_for_character(_character())
        self.assertEqual(
            (pair.current_hp, pair.max_hp, pair.source),
            (player_wire.PLAYER_LOGIN_HP_CURRENT,
             player_wire.PLAYER_LOGIN_HP_MAX,
             wrpa.PRESENCE_HP_SOURCE_LOGIN_CONSTANTS),
        )

    def test_the_constants_are_read_from_player_wire_not_copied_here(self):
        """If ``player_wire`` ever changes its login pair, this door must
        move with it -- a hardcoded 100 here would show a second player a bar
        its own client is not showing.

        THIS TEST USED TO GREP THE SOURCE FOR THE TWO NAMES, and pf-adversary
        round q6a8oa (finding D2) broke it in one move: replacing the read
        with ``100, 100`` left the names standing in a docstring and the
        whole file stayed green.  A test that cannot be made to fail is a
        printout.  So: patch the constants to values nothing else in this
        tree uses, and watch the door move.  It pins the ORDER too (finding
        D8) -- the real constants are both 100, so a current/max swap in that
        branch survived every earlier test in this file."""
        with mock.patch.object(player_wire, "PLAYER_LOGIN_HP_CURRENT", 37), \
                mock.patch.object(player_wire, "PLAYER_LOGIN_HP_MAX", 91):
            pair = wrpa.hp_pair_for_character(_character())
        self.assertEqual(
            (pair.current_hp, pair.max_hp, pair.source),
            (37, 91, wrpa.PRESENCE_HP_SOURCE_LOGIN_CONSTANTS),
        )

    def test_a_row_with_a_pair_but_no_level_is_refused_not_believed(self):
        """The rule this door cites is ALL THREE OR NONE, and
        ``legacy_bridge.start_game`` enforces it on the very same row:
        ``level is not None and hp_current is not None and hp_max is not
        None``.  A row carrying 380/520 beside a ``None`` level is a row
        whose own login sent the CONSTANTS, so answering 380/520 here would
        show the second player a bar the first player is not looking at.
        (pf-adversary round q6a8oa, finding D3: the earlier door cited the
        three-value rule and guarded two of the three.)"""
        with self.assertRaises(wrpa.RemotePlayerActorRefusal) as caught:
            wrpa.hp_pair_for_character(
                _character(hp=380, hp_max=520, level=None))
        self.assertIn(wrpa.PRESENCE_REFUSED_LOGIN_VITALS_PARTIAL,
                      str(caught.exception))

    def test_the_door_and_legacy_bridge_agree_on_every_vitals_shape(self):
        """Not "the same words" -- the same ANSWER, on every combination of
        set/unset the three vitals can take, measured against what
        ``legacy_bridge.start_game`` would actually put on that character's
        own login wire."""
        for level in (None, 1):
            for hp in (None, 380):
                for hp_max in (None, 520):
                    row = _character(hp=hp, hp_max=hp_max, level=level)
                    wire_sends_the_row = (
                        level is not None and hp is not None
                        and hp_max is not None)
                    with self.subTest(shape=(level, hp, hp_max)):
                        if wire_sends_the_row:
                            pair = wrpa.hp_pair_for_character(row)
                            self.assertEqual(
                                (pair.current_hp, pair.max_hp, pair.source),
                                (hp, hp_max, wrpa.PRESENCE_HP_SOURCE_ROW))
                        elif (level, hp, hp_max) == (None, None, None):
                            pair = wrpa.hp_pair_for_character(row)
                            self.assertEqual(
                                pair.source,
                                wrpa.PRESENCE_HP_SOURCE_LOGIN_CONSTANTS)
                        else:
                            with self.assertRaises(
                                    wrpa.RemotePlayerActorRefusal):
                                wrpa.hp_pair_for_character(row)

    def test_a_pair_above_the_registry_ceiling_is_refused_by_name(self):
        """D10: this door borrowed the registry's ceiling without pinning it.
        Now it refuses by a name of its own -- the registry's own answer is a
        bare outcome that never says "too big"."""
        with self.assertRaises(wrpa.RemotePlayerActorRefusal) as caught:
            wrpa.hp_pair_for_character(
                _character(hp=1, hp_max=wrpa.PRESENCE_HP_CEILING + 1))
        self.assertIn(wrpa.PRESENCE_REFUSED_HP_ABOVE_CEILING,
                      str(caught.exception))

    def test_the_copied_ceiling_still_equals_the_registrys_own(self):
        """A copied constant that silently drifts from the original is worse
        than no constant: this door would start accepting pairs the registry
        then refuses namelessly."""
        self.assertEqual(wrpa.PRESENCE_HP_CEILING,
                         getattr(wsr, "_MAX_HP"))

    def test_a_bool_is_not_an_int_here_either(self):
        """The guard that catches this is now a single condition (the
        ``or type(value) is bool`` half was dead: ``type(True) is int`` is
        already False).  Pinned so the surviving half is load-bearing."""
        with self.assertRaises(wrpa.RemotePlayerActorRefusal) as caught:
            wrpa.hp_pair_for_character(_character(hp=True, hp_max=True))
        self.assertIn(wrpa.PRESENCE_REFUSED_HP_PAIR_NOT_INTS,
                      str(caught.exception))

    def test_a_row_that_carries_its_own_pair_answers_that_pair(self):
        pair = wrpa.hp_pair_for_character(_character(hp=380, hp_max=520))
        self.assertEqual(
            (pair.current_hp, pair.max_hp, pair.source),
            (380, 520, wrpa.PRESENCE_HP_SOURCE_ROW),
        )

    def test_half_a_pair_is_refused_rather_than_completed_from_constants(self):
        for row in (_character(hp=380), _character(hp_max=520)):
            with self.subTest(row=(row.hp_current, row.hp_max)):
                with self.assertRaises(wrpa.RemotePlayerActorRefusal) as caught:
                    wrpa.hp_pair_for_character(row)
                self.assertIn(wrpa.PRESENCE_REFUSED_HP_PAIR_HALF_SET,
                              str(caught.exception))

    def test_a_zero_current_is_refused_because_zero_is_the_death_predicate(self):
        with self.assertRaises(wrpa.RemotePlayerActorRefusal) as caught:
            wrpa.hp_pair_for_character(_character(hp=0, hp_max=520))
        self.assertIn(wrpa.PRESENCE_REFUSED_HP_CURRENT_BELOW_ONE,
                      str(caught.exception))

    def test_a_zero_max_is_refused_too(self):
        with self.assertRaises(wrpa.RemotePlayerActorRefusal) as caught:
            wrpa.hp_pair_for_character(_character(hp=1, hp_max=0))
        self.assertIn(wrpa.PRESENCE_REFUSED_HP_MAX_BELOW_ONE,
                      str(caught.exception))

    def test_current_above_max_is_refused(self):
        with self.assertRaises(wrpa.RemotePlayerActorRefusal) as caught:
            wrpa.hp_pair_for_character(_character(hp=521, hp_max=520))
        self.assertIn(wrpa.PRESENCE_REFUSED_HP_CURRENT_ABOVE_MAX,
                      str(caught.exception))

    def test_a_pair_that_is_not_two_ints_is_refused(self):
        for bad in ((380.0, 520), (380, True), ("380", 520)):
            with self.subTest(bad=bad):
                with self.assertRaises(wrpa.RemotePlayerActorRefusal) as caught:
                    wrpa.hp_pair_for_character(
                        _character(hp=bad[0], hp_max=bad[1]))
                self.assertIn(wrpa.PRESENCE_REFUSED_HP_PAIR_NOT_INTS,
                              str(caught.exception))


class RegisterPresenceForACharacterRow(unittest.TestCase):
    """The one-argument write door the runtime paste sites need."""

    def setUp(self):
        self.book = wsr.WorldSceneRegistry()

    def test_the_row_lands_with_the_name_position_and_pair_of_the_character(self):
        outcome = wrpa.register_presence_for_character(
            _character(identity=4242, name="Somchai", hp=380, hp_max=520,
                       xyz=(1.5, 2.5, 3.5)),
            registry=self.book,
        )
        self.assertTrue(outcome.noted, outcome.reason)
        remembered = outcome.remembered
        self.assertEqual(remembered.actor_identity, 4242)
        self.assertEqual(remembered.name, "Somchai")
        self.assertEqual((remembered.current_hp, remembered.max_hp), (380, 520))
        self.assertEqual(
            (remembered.position[0], remembered.position[1],
             remembered.position[2]),
            (1.5, 2.5, 3.5),
        )

    def test_position_overrides_the_row_and_nothing_else(self):
        outcome = wrpa.register_presence_for_character(
            _character(identity=99, scene_id=1, xyz=(0.0, 0.0, 0.0)),
            position=(700.0, 800.0, 900.0), registry=self.book,
        )
        self.assertTrue(outcome.noted, outcome.reason)
        self.assertEqual(
            tuple(outcome.remembered.position[:3]), (700.0, 800.0, 900.0))
        self.assertEqual(outcome.remembered.actor_identity, 99)

    def test_a_dishonest_pair_refuses_by_name_and_writes_nothing(self):
        outcome = wrpa.register_presence_for_character(
            _character(identity=5, hp=0, hp_max=100), registry=self.book)
        self.assertFalse(outcome.noted)
        self.assertEqual(outcome.reason,
                         wrpa.PRESENCE_REFUSED_HP_CURRENT_BELOW_ONE)
        legacy = load_legacy(LEGACY_PATH)
        # Nothing was written: a viewer standing in that scene is composed a
        # frame with no actors in it at all.
        self.assertEqual(
            wrpa.compose_other_live_players_frame(
                legacy, 1, 7001, registry=self.book).actor_count,
            0,
        )

    def test_a_row_without_a_position_refuses_and_never_raises(self):
        class NoPosition:
            id = 5
            name = "x"
            hp_current = None
            hp_max = None
            position = None

        outcome = wrpa.register_presence_for_character(
            NoPosition(), registry=self.book)
        self.assertFalse(outcome.noted)
        self.assertEqual(outcome.reason, wrpa.PRESENCE_REFUSED_NO_POSITION)

    def test_the_registered_row_is_what_the_other_session_is_composed_from(self):
        legacy = load_legacy(LEGACY_PATH)
        wrpa.register_presence_for_character(
            _character(identity=4242, name="Somchai", scene_id=1,
                       hp=380, hp_max=520),
            registry=self.book,
        )
        mine = wrpa.compose_other_live_players_frame(
            legacy, 1, 7001, registry=self.book)
        self.assertEqual(mine.actor_count, 1)
        self.assertEqual(mine.identities, (4242,))
        # ...and the viewer never receives themselves, the invariant this
        # file already pins for hand-written rows, re-pinned through the new
        # door because that is the door a real login will use.
        theirs = wrpa.compose_other_live_players_frame(
            legacy, 1, 4242, registry=self.book)
        self.assertEqual(theirs.actor_count, 0)


    def test_no_shape_a_call_site_could_hand_it_makes_it_raise(self):
        """The door sits on the login and movement paths.  An exception
        there takes the session down with it, so every hostile shape must
        come back as a NAMED outcome -- and a nameless one (empty reason on
        a row that did not land) would be just as bad as a raise."""
        class NoAttributesAtAll:
            pass

        cases = {
            "no attributes": NoAttributesAtAll(),
            "None": None,
            "position is not a position": type(
                "X", (), {"position": 5, "id": 1, "name": "a"})(),
            "scene id is a bool": type("X", (), {
                "position": model.Position(True, 0, 1.0, 2.0, 3.0),
                "id": 1, "name": "a", "hp_current": None, "hp_max": None})(),
            "name is None": _character(name=None),
            "identity is None": _character(identity=None),
            "scene nothing addresses": _character(scene_id=99999),
        }
        for label, row in cases.items():
            with self.subTest(row=label):
                outcome = wrpa.register_presence_for_character(
                    row, registry=self.book)
                self.assertFalse(outcome.noted)
                self.assertTrue(outcome.reason)

    def test_a_position_override_of_the_wrong_shape_is_refused_not_written(self):
        outcome = wrpa.register_presence_for_character(
            _character(identity=3), position=[1, 2], registry=self.book)
        self.assertFalse(outcome.noted)
        self.assertTrue(outcome.reason)


class TheAskNoLongerCarriesAnOpenQuestion(unittest.TestCase):

    def test_no_placeholder_survives_in_the_pasteable_ask(self):
        text = wrpa.PLAYER_PRESENCE_WIRING
        for placeholder in ("<current hp>", "<max hp>", "<hp>", "<max_hp>",
                            "<name>"):
            with self.subTest(placeholder=placeholder):
                self.assertNotIn(placeholder, text)

    def test_the_ask_names_the_one_argument_door(self):
        self.assertIn("register_presence_for_character",
                      wrpa.PLAYER_PRESENCE_WIRING)
        self.assertIn("register_presence_for_login(",
                      wrpa.PLAYER_PRESENCE_WIRING)


class ThePositionAPresenceRowCarries(unittest.TestCase):
    """pf-adversary round q6a8oa, finding D1 -- the HIGH this round exists
    to pay.

    A login resolves ONE position and sends THAT to the client.  On the GM
    login-scene-override path the stored row it was resolved from still
    names the scene the player came FROM, and runtime.py only replaces the
    in-memory row's position AFTER the frames are built.  A presence row is
    read to tell OTHER players where somebody is standing, so it must carry
    the point the client was sent -- not the row the point came from.
    """

    def setUp(self):
        self.book = wsr.WorldSceneRegistry()

    @staticmethod
    def _entry(scene_id, xyz=(11.0, 22.0, 33.0)):
        """A real entry from the real resolver -- the same object
        ``resolve_entry`` hands ``runtime.py`` on the login path, built the
        same way.  Not a stand-in, deliberately: a stub could agree with a
        door that had misread what ``SceneEntry`` promises."""
        return wse.resolve_entry(
            model.Position(scene_id, 0, xyz[0], xyz[1], xyz[2]),
            emit=lambda *a, **k: None,
        )

    def test_the_resolved_entry_wins_over_the_row_scene_included(self):
        entry = self._entry(2)
        point = wrpa.presence_position_for_login(
            _character(scene_id=1, xyz=(10.0, 20.0, 30.0)), entry)
        self.assertEqual(
            (point.scene_id, point.x, point.y, point.z, point.source),
            (entry.position.scene_id, entry.position.x, entry.position.y,
             entry.position.z, wrpa.PRESENCE_POSITION_SOURCE_RESOLVED_ENTRY),
        )
        # And it is the RESOLVED point, not the one that was asked for: this
        # entry relocated to the destination's pinned spawn, which is what
        # the client was actually sent.
        self.assertTrue(entry.relocated)
        self.assertNotEqual((point.x, point.y, point.z), (11.0, 22.0, 33.0))

    def test_no_entry_means_the_rows_own_position(self):
        point = wrpa.presence_position_for_login(
            _character(scene_id=1, xyz=(10.0, 20.0, 30.0)))
        self.assertEqual(
            (point.scene_id, point.x, point.source),
            (1, 10.0, wrpa.PRESENCE_POSITION_SOURCE_ROW),
        )

    def test_the_overridden_login_is_visible_where_the_player_is_standing(self):
        """THE MEASUREMENT THAT FAILED IN REVISION 1, re-run through the
        door revision 2 asks chief to paste.  Row says scene 1, the login
        resolved scene 2 and sent scene 2 to the client.  A viewer standing
        in scene 2 must see this player; scene 1 must be empty of them."""
        legacy = load_legacy(LEGACY_PATH)
        entry = self._entry(2)
        outcome = wrpa.register_presence_for_login(
            _character(identity=4242, scene_id=1), entry, registry=self.book,
        )
        self.assertTrue(outcome.noted, outcome.reason)
        self.assertEqual(entry.position.scene_id, 2)
        seen_in_two = wrpa.compose_other_live_players_frame(
            legacy, 2, 7001, registry=self.book)
        self.assertEqual(seen_in_two.identities, (4242,))
        seen_in_one = wrpa.compose_other_live_players_frame(
            legacy, 1, 7001, registry=self.book)
        self.assertEqual(seen_in_one.actor_count, 0)

    def test_without_the_entry_the_same_login_lands_in_the_wrong_scene(self):
        """The bug, pinned as a bug: this is what the revision-1 paste did,
        and it is why the ``entry`` argument exists.  If this test ever goes
        green with the same numbers as the one above, the argument stopped
        doing anything."""
        legacy = load_legacy(LEGACY_PATH)
        wrpa.register_presence_for_login(
            _character(identity=4242, scene_id=1), None, registry=self.book)
        self.assertEqual(
            wrpa.compose_other_live_players_frame(
                legacy, 2, 7001, registry=self.book).actor_count,
            0,
        )
        self.assertEqual(
            wrpa.compose_other_live_players_frame(
                legacy, 1, 7001, registry=self.book).identities,
            (4242,),
        )

    def test_an_entry_whose_position_is_unusable_refuses_by_name(self):
        outcome = wrpa.register_presence_for_login(
            _character(identity=9),
            type("BadEntry", (), {"position": None})(),
            registry=self.book,
        )
        self.assertFalse(outcome.noted)
        self.assertEqual(outcome.reason,
                         wrpa.PRESENCE_REFUSED_ENTRY_HAS_NO_POSITION)

    def test_a_movement_report_still_overrides_only_the_point(self):
        """Call site (2) passes ``position=`` and no entry: same character,
        same scene, fresher point.  The scene must come from the row, and
        the row alone."""
        legacy = load_legacy(LEGACY_PATH)
        outcome = wrpa.register_presence_for_character(
            _character(identity=51, scene_id=2, xyz=(0.0, 0.0, 0.0)),
            position=(700.0, 800.0, 900.0), registry=self.book,
        )
        self.assertTrue(outcome.noted, outcome.reason)
        self.assertEqual(
            tuple(outcome.remembered.position[:3]), (700.0, 800.0, 900.0))
        self.assertEqual(
            wrpa.compose_other_live_players_frame(
                legacy, 2, 7001, registry=self.book).identities,
            (51,),
        )
        self.assertEqual(
            wrpa.compose_other_live_players_frame(
                legacy, 1, 7001, registry=self.book).actor_count,
            0,
        )

    def test_the_entry_type_this_door_reads_really_has_a_position(self):
        """The door reads ``entry.position``.  If ``SceneEntry`` ever
        renames that field, this fails here rather than silently falling
        back to the row on every login."""
        self.assertIn("position", wse.SceneEntry.__dataclass_fields__)


class ARefusedPresenceWriteSaysSoOutLoud(unittest.TestCase):
    """pf-adversary round q6a8oa, finding D5.

    A refused presence write means that player is INVISIBLE to every other
    session in the scene.  Until this round that happened without a byte on
    the console, in a file whose neighbours in runtime.py all announce
    (``BACKPACK_LOAD_REFUSED``, ``GM_LOGIN_SCENE_OVERRIDE_CONSUME_FAILED``).
    """

    def setUp(self):
        self.book = wsr.WorldSceneRegistry()

    def _register(self, row, **kwargs):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            outcome = wrpa.register_presence_for_character(
                row, registry=self.book, **kwargs)
        return outcome, buffer.getvalue()

    def test_every_refusal_this_door_can_answer_prints_its_reason(self):
        cases = {
            "no position": type("X", (), {"position": None, "id": 3,
                                          "name": "a"})(),
            "hp zero": _character(identity=5, hp=0, hp_max=100),
            "half a pair": _character(identity=6, hp=380),
            "partial vitals": _character(identity=7, hp=380, hp_max=520,
                                         level=None),
            "hp not ints": _character(identity=8, hp="380", hp_max=520),
            "above the ceiling": _character(
                identity=9, hp=1, hp_max=wrpa.PRESENCE_HP_CEILING + 1),
            "scene nothing addresses": _character(identity=10,
                                                  scene_id=99999),
        }
        for label, row in cases.items():
            with self.subTest(case=label):
                outcome, printed = self._register(row)
                self.assertFalse(outcome.noted)
                self.assertIn(wrpa.PRESENCE_REFUSED_CONSOLE_TOKEN, printed)
                self.assertIn(outcome.reason, printed)
                printed.encode("ascii")

    def test_a_write_that_lands_says_nothing(self):
        outcome, printed = self._register(
            _character(identity=4242, hp=380, hp_max=520))
        self.assertTrue(outcome.noted, outcome.reason)
        self.assertEqual(printed, "")

    def test_a_name_the_console_cannot_encode_never_reaches_the_console(self):
        """The bridge console is cp874.  One non-ASCII byte out of a name or
        a repr takes the print -- and with it the login -- down."""
        outcome, printed = self._register(
            _character(identity=11, name="\u0e1b\u0e31\u0e0d\u0e0d\u0e32",
                       scene_id=99999))
        self.assertFalse(outcome.noted)
        printed.encode("ascii")
        self.assertIn(wrpa.PRESENCE_REFUSED_CONSOLE_TOKEN, printed)

    def test_a_broken_stdout_does_not_take_the_login_down(self):
        class Exploding(io.StringIO):
            def write(self, _text):
                raise OSError("the console went away")

        with redirect_stdout(Exploding()):
            outcome = wrpa.register_presence_for_character(
                _character(identity=12, hp=0, hp_max=100), registry=self.book)
        self.assertFalse(outcome.noted)
        self.assertEqual(outcome.reason,
                         wrpa.PRESENCE_REFUSED_HP_CURRENT_BELOW_ONE)

    def test_the_token_is_one_word_a_log_scraper_can_grep(self):
        self.assertEqual(wrpa.PRESENCE_REFUSED_CONSOLE_TOKEN.split(),
                         [wrpa.PRESENCE_REFUSED_CONSOLE_TOKEN])


if __name__ == "__main__":
    unittest.main()
