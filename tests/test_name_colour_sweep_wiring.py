"""RE-155's dummy row on the REAL dispatcher -- armed and, above all, unarmed.

``tests/test_name_colour_sweep.py`` (LANE-B's own) proves the builder offline:
which candidates exist, how each differs from its BASE by one field, what the
refusals are.  It cannot say whether anything reaches a client, because until
the wire this file pins, nothing in ``src/`` imported the module at all -- that
was the whole content of LANE-B's CORE-REQUEST to chief
(``pf_bridge notes_to_chief/20260907_0027``).

What this file proves, on the same headless ``make_state_class`` harness
``tests/test_world_census_wiring.py`` uses -- no server process, no socket, no
client:

  * UNARMED IS THE POINT.  A default boot with ``PF_NAME_COLOUR_SWEEP`` absent
    queues exactly the actions it queued before the wire existed: the two
    ``WORLD_CENSUS_*`` entries and nothing else from this lane.  This is
    asserted against a cleared environment rather than against "whatever the
    test runner happened to inherit", because the module reads ``os.environ``
    directly and a leaked variable from another test would make an armed boot
    look like the default one.
  * ARMED, the row goes out INSIDE the census collection and there is NO
    second ``RuntimeRemoteActors`` frame anywhere.  This is the correction
    round ``ky8m6j`` owed round ``52u95a``: RE-092 measured this client's
    remote-actor consumer as replace-by-omission at COLLECTION scope, so a
    second frame carrying only the dummies would have replaced the whole town
    with them and destroyed the ``N-BASE`` control the ticket reads against.
    The regression test for that is
    ``test_no_second_collection_is_ever_queued``, and it is the most important
    assertion in this file.
  * The merged bytes carry the module's own entries -- compared against an
    independently computed ``sweep_entries``, not against a reconstruction of
    the dispatch's arithmetic -- and the wire count equals census + row.
  * ``generation``/``world_census_actor_count`` keep counting the CENSUS.  A
    widened count is handed back to ``build_world_population`` on every later
    recompose, which refuses a count above ``CENSUS_COUNT``, and RE-092 says a
    compose failure there empties the town.
  * Every refusal path is EXECUTED here, not described: a sibling exception
    from the module (``FieldMobContractError``, which is NOT a
    ``NameColourSweepError``) and a merge failure both leave the ordinary
    census queued and the listener thread alive.
  * The sweep's actor identities are disjoint from the census's, and are
    deliberately absent from ``mob_combat_announced_membership``: the row is a
    read-only colour instrument, not something killable.

NOT proven here, and not provable without a person at a screen: whether the
client draws any of these dummies at all, and what colour it paints their
names.  That is the whole reason RE-155 exists and it is an attended ticket,
not a test.  No count is written into this file's prose on purpose -- the two
armed sets have different sizes (set 1 measured 8 actors, set 2 six) and a
prose count is the kind of thing that goes stale silently; the assertions read
the count back from the module instead.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import name_colour_sweep  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

SWEEP_LABEL_PREFIX = "NAME_COLOUR_SWEEP_"
CENSUS_LABEL_PREFIX = "WORLD_CENSUS_"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class NameColourSweepWiringTests(unittest.TestCase):
    """The harness is a deliberate copy of ``test_world_census_wiring.py``'s.

    Not imported from it: that file's helpers are private to its own class and
    importing a TestCase's methods across files couples two lanes' test files
    together in a way this house has been bitten by before (a rename in one
    file turning another lane's suite red).  The duplication is four short
    methods and it is on purpose.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
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

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ----------------------------------------------------------

    def _state(self, token, **kwargs):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector, **kwargs,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return state

    def _target_pos_pc(self, xyz, heading=0.0, moving=0, derived=0):
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + b"".join(
                self.legacy.f32tag(value) for value in (*xyz, heading)
            )
            + self.legacy.u8tag(0x0B, moving)
            + self.legacy.u8tag(0x0B, derived)
        )

    def _step(self, state, xyz=(10.0, 20.0, 30.0), **kwargs):
        return state.dispatch(
            self.legacy.parse_outer(self._target_pos_pc(xyz, **kwargs))
        )

    def _labelled(self, actions, prefix):
        return [action for action in actions if action[0].startswith(prefix)]

    def _arrive(self, token, env_value):
        """One default boot's arrival frame, with the env pinned EXACTLY.

        ``clear=True`` matters more than the value does: the wire calls
        ``build_sweep_population(legacy)`` with no ``env`` argument, so it
        reads the process environment, and an unarmed assertion made against
        an environment this test did not control would prove nothing.
        """
        env = {} if env_value is None else {name_colour_sweep.SWEEP_ENV: env_value}
        with mock.patch.dict(os.environ, env, clear=True):
            state = self._state(token)
            return self._step(state)

    # ----- unarmed ----------------------------------------------------------

    def test_an_unarmed_boot_queues_no_sweep_action(self):
        actions = self._arrive("sweep-unarmed-1", None)
        self.assertEqual(self._labelled(actions, SWEEP_LABEL_PREFIX), [])

    def test_an_unarmed_boot_still_queues_its_two_census_actions(self):
        """The wire is additive or it is a regression -- there is no third
        state.  If the block ever raises or returns early before the census
        is queued, this is the test that says so rather than the attended
        tester finding an empty town.
        """
        actions = self._arrive("sweep-unarmed-2", None)
        labels = [a[0] for a in self._labelled(actions, CENSUS_LABEL_PREFIX)]
        self.assertEqual(len(labels), 2, labels)
        self.assertTrue(labels[0].startswith("WORLD_CENSUS_INITIAL_"), labels)
        self.assertTrue(labels[1].startswith("WORLD_CENSUS_REAPPLY_"), labels)

    def test_an_unknown_env_value_is_unarmed_not_an_error(self):
        """Fail-closed on a typo.  A tester who exports
        ``PF_NAME_COLOUR_SWEEP=true`` gets an ordinary boot and no row, not a
        dead listener thread and not a half-composed one.
        """
        actions = self._arrive("sweep-typo", "true")
        self.assertEqual(self._labelled(actions, SWEEP_LABEL_PREFIX), [])
        self.assertEqual(
            len(self._labelled(actions, CENSUS_LABEL_PREFIX)), 2,
        )

    # ----- armed ------------------------------------------------------------

    def _arrive_capturing(self, token, env_value):
        """``_arrive``, with the console this boot printed captured too."""
        env = ({} if env_value is None
               else {name_colour_sweep.SWEEP_ENV: env_value})
        console = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True):
            with contextlib.redirect_stdout(console):
                state = self._state(token)
                actions = self._step(state)
        return state, actions, console.getvalue()

    def test_no_second_collection_is_ever_queued(self):
        """THE RE-092 REGRESSION TEST.  Round ``52u95a`` queued the row as its
        own ``make_runtime_remote_actors`` frame; RE-092 (2026-08-26 22:23)
        had already measured that a later collection REPLACES the actor set,
        so that frame would have erased every real NPC in Port Royal and left
        the ticket reading colours off eight dummies in an empty town.  Armed
        or unarmed, this dispatch queues exactly two actions from this branch.
        """
        for env_value in (
            name_colour_sweep.SET_FACTION,
            name_colour_sweep.SET_ACTOR_TYPE_AND_SKIN,
        ):
            with self.subTest(env_value=env_value):
                actions = self._arrive(f"sweep-one-frame-{env_value}",
                                       env_value)
                self.assertEqual(
                    self._labelled(actions, SWEEP_LABEL_PREFIX), [],
                )
                census = self._labelled(actions, CENSUS_LABEL_PREFIX)
                self.assertEqual(len(census), 2, [a[0] for a in actions])

    def test_both_census_actions_carry_the_same_merged_bytes(self):
        """The row arrives WITH the census and is still there after the
        reapply repeats it.  Two identical frames is what the census already
        did before this lane existed; the sweep does not change that shape.
        """
        actions = self._arrive("sweep-both", name_colour_sweep.SET_FACTION)
        census = self._labelled(actions, CENSUS_LABEL_PREFIX)
        self.assertEqual(census[0][1], census[1][1])
        self.assertEqual(census[0][2], census[1][2])
        self.assertEqual(
            [census[0][3], census[1][3]],
            [0.0, world_population.INITIAL_REAPPLY_MS / 1000.0],
        )

    def test_the_merged_bytes_carry_the_modules_own_entries(self):
        """Compared against an INDEPENDENT build, not against a rebuild of the
        dispatch's own arithmetic: the point is that the dispatcher ships what
        LANE-B's module composed, byte for byte, inside its own collection.
        """
        env = {name_colour_sweep.SWEEP_ENV: name_colour_sweep.SET_FACTION}
        with mock.patch.dict(os.environ, env, clear=True):
            state = self._state("sweep-bytes")
            actions = self._step(state)
            expected = name_colour_sweep.sweep_entries(self.legacy)
        self.assertTrue(expected)
        pc = self._labelled(actions, CENSUS_LABEL_PREFIX)[0][1]
        for position, entry in enumerate(expected):
            with self.subTest(entry=position):
                self.assertIn(entry, pc)
        start = world_population.WIRE_COUNT_TAG_OFFSET + 1
        self.assertEqual(
            int.from_bytes(pc[start:start + 2], "little"),
            state.world_census_actor_count + len(expected),
        )

    def test_the_label_carries_the_sweep_count_at_send_time(self):
        """v141 prints ``[G>] <label> (N bytes)`` per queued action at SEND
        time, so the label is the only sweep token an attended tester sees
        that proves the row left the server.  The compose-time console line
        cannot: a socket that dropped between composing and sending prints
        exactly the same thing.
        """
        for env_value in (
            name_colour_sweep.SET_FACTION,
            name_colour_sweep.SET_ACTOR_TYPE_AND_SKIN,
        ):
            with self.subTest(env_value=env_value):
                env = {name_colour_sweep.SWEEP_ENV: env_value}
                with mock.patch.dict(os.environ, env, clear=True):
                    state = self._state(f"sweep-label-{env_value}")
                    actions = self._step(state)
                    expected = len(name_colour_sweep.sweep_actors(self.legacy))
                labels = [
                    a[0] for a in self._labelled(actions, CENSUS_LABEL_PREFIX)
                ]
                self.assertEqual(len(labels), 2, labels)
                for label in labels:
                    self.assertTrue(
                        label.endswith(f"_SWEEP_{expected}"), label,
                    )

    def test_the_census_bookkeeping_still_counts_only_the_census(self):
        """``world_census_actor_count`` is handed back to
        ``build_world_population`` on every recompose, which refuses a count
        above ``CENSUS_COUNT``.  A "helpfully" widened count would turn the
        first hit of the boot into a compose failure -- and RE-092 says a
        compose failure empties the town.
        """
        armed_state, _actions, _console = self._arrive_capturing(
            "sweep-count-armed", name_colour_sweep.SET_FACTION,
        )
        control_state, _actions, _console = self._arrive_capturing(
            "sweep-count-unarmed", None,
        )
        self.assertEqual(
            armed_state.world_census_actor_count,
            control_state.world_census_actor_count,
        )
        self.assertEqual(
            armed_state.world_census_indices,
            control_state.world_census_indices,
        )
        self.assertEqual(
            armed_state.census_anchor_record.actor_count,
            control_state.census_anchor_record.actor_count,
        )

    def test_a_sibling_exception_from_the_module_is_caught_not_escaped(self):
        """``NameColourSweepError`` and ``field_mobs.FieldMobContractError``
        are SIBLINGS -- both subclass ``ValueError``, neither subclasses the
        other -- so the narrow ``except NameColourSweepError`` round ``52u95a``
        wrote never covered the ``load_roster``/``hostile_npc_attr`` raises
        this path walks through.  An escape here unwinds the listener thread
        (v141:7440 has no ``except``).  This test EXECUTES that path rather
        than describing it.
        """
        env = {name_colour_sweep.SWEEP_ENV: name_colour_sweep.SET_FACTION}
        console = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(
                name_colour_sweep, "sweep_entries",
                side_effect=field_mobs.FieldMobContractError("roster drift"),
            ):
                with contextlib.redirect_stdout(console):
                    state = self._state("sweep-sibling-raise")
                    actions = self._step(state)
        labels = [a[0] for a in self._labelled(actions, CENSUS_LABEL_PREFIX)]
        self.assertEqual(len(labels), 2, labels)
        for label in labels:
            self.assertNotIn("_SWEEP_", label)
        self.assertIn(
            "name_colour_sweep_refused_FieldMobContractError", state.events,
        )
        self.assertIn("NAME_COLOUR_SWEEP_REFUSED", console.getvalue())
        self.assertIn("roster drift", console.getvalue())

    def test_a_merge_refusal_ships_the_untouched_census(self):
        """Fail closed to the town that shipped yesterday.  An armed boot that
        cannot splice must send the ordinary census, not a half-built frame
        and not nothing.
        """
        env = {name_colour_sweep.SWEEP_ENV: name_colour_sweep.SET_FACTION}
        console = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(
                world_population, "append_census_entries",
                side_effect=ValueError("appended-census frame drift"),
            ):
                with contextlib.redirect_stdout(console):
                    state = self._state("sweep-merge-refused")
                    armed = self._step(state)
        armed_census = self._labelled(armed, CENSUS_LABEL_PREFIX)
        self.assertEqual(len(armed_census), 2)
        # The census that shipped is this session's OWN untouched census --
        # asserted against its wire count and its label, not against another
        # session's bytes: the arrival census carries a per-viewer identity
        # (CORE-REQUEST-GM-061), so two sessions never agree byte for byte.
        start = world_population.WIRE_COUNT_TAG_OFFSET + 1
        for label, pc, _frame, _delay in armed_census:
            self.assertNotIn("_SWEEP_", label)
            self.assertEqual(
                int.from_bytes(pc[start:start + 2], "little"),
                state.world_census_actor_count,
            )
        self.assertIn(
            "name_colour_sweep_merge_refused_ValueError", state.events,
        )
        self.assertIn("NAME_COLOUR_SWEEP_MERGE_REFUSED", console.getvalue())

    def test_an_unknown_env_value_says_so_on_the_console(self):
        """A typo used to boot an ordinary town in TOTAL silence -- byte for
        byte and line for line identical to a build with no sweep in it, so a
        tester could not tell ``PF_NAME_COLOUR_SWEEP=true`` from a stale
        binary.  Now the console names the value it refused.
        """
        _state, actions, console = self._arrive_capturing(
            "sweep-typo-console", "true",
        )
        self.assertEqual(len(self._labelled(actions, CENSUS_LABEL_PREFIX)), 2)
        self.assertIn("NAME_COLOUR_SWEEP_UNARMED value=", console)
        self.assertIn("true", console)
        self.assertIn(
            "name_colour_sweep_unarmed_unknown_value", _state.events,
        )

    def test_an_unarmed_boot_prints_no_sweep_line_at_all(self):
        """The other half of the line above: the console stays clean on every
        ordinary boot, so the token means something when it appears.
        """
        _state, _actions, console = self._arrive_capturing(
            "sweep-silent", None,
        )
        self.assertNotIn("NAME_COLOUR_SWEEP", console)

    def test_the_sweep_identities_are_on_the_wire_but_not_in_combat_membership(
            self):
        """A shared actor identity would put a dummy and a real bg0001 mob in
        the same slot of the client's collection.  And the dummies stay OUT of
        ``mob_combat_announced_membership`` on purpose: the row is a read-only
        colour instrument, so a swing at one is declined rather than accepted
        into a combat state nothing here maintains.
        """
        env = {name_colour_sweep.SWEEP_ENV: name_colour_sweep.SET_FACTION}
        with mock.patch.dict(os.environ, env, clear=True):
            state = self._state("sweep-identities")
            self._step(state)
            sweep_identities = {
                actor.actor_identity
                for actor in name_colour_sweep.sweep_actors(self.legacy)
            }
        census_identities = set(
            state.mob_combat_announced_membership.actor_identities
        )
        self.assertTrue(sweep_identities)
        self.assertEqual(sweep_identities & census_identities, set())

    def test_the_row_is_merged_once_per_session_not_once_per_frame(self):
        """The census branch is one-shot per session (``world_census_sent``
        latches).  The sweep is inside it, so it inherits that -- but the
        inheritance is the claim, and a future edit that moves the block one
        indent level out would silently re-send the row on every step.
        """
        env = {name_colour_sweep.SWEEP_ENV: name_colour_sweep.SET_FACTION}
        with mock.patch.dict(os.environ, env, clear=True):
            state = self._state("sweep-once")
            first = self._step(state)
            second = self._step(state, xyz=(11.0, 21.0, 31.0))
            third = self._step(state, xyz=(12.0, 22.0, 32.0))
        self.assertTrue(
            all("_SWEEP_" in a[0]
                for a in self._labelled(first, CENSUS_LABEL_PREFIX))
        )
        self.assertEqual(self._labelled(second, CENSUS_LABEL_PREFIX), [])
        self.assertEqual(self._labelled(third, CENSUS_LABEL_PREFIX), [])


class AppendCensusEntriesTests(unittest.TestCase):
    """``world_population.append_census_entries`` on its own.

    The sibling of ``apply_identity_override``: that one REPLACES entry bytes
    for identities the census already carries, this one APPENDS bodies it
    never had.  Every refusal below is a shape that would otherwise reach
    ``make_runtime_remote_actors`` and mis-tell the client how many bodies
    follow -- the stream-tail misalignment this client answers with
    ErrorData=28317.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def _generation(self):
        anchor = (100.0, 200.0, 300.0)
        return world_population.build_world_population(
            self.legacy, anchor, 3,
            scene_id=world_population.SCENE_ID,
        )

    def test_appending_nothing_returns_the_untouched_bytes(self):
        generation = self._generation()
        pc, frame = world_population.append_census_entries(
            self.legacy, generation, (),
        )
        self.assertEqual(pc, generation.pc)
        self.assertEqual(frame, generation.frame)

    def test_appending_widens_the_wire_count_and_keeps_the_originals(self):
        generation = self._generation()
        extra = name_colour_sweep.sweep_entries(
            self.legacy, {name_colour_sweep.SWEEP_ENV:
                          name_colour_sweep.SET_FACTION},
        )
        self.assertTrue(extra)
        pc, frame = world_population.append_census_entries(
            self.legacy, generation, extra,
        )
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        start = world_population.WIRE_COUNT_TAG_OFFSET + 1
        self.assertEqual(
            int.from_bytes(pc[start:start + 2], "little"),
            generation.actor_count + len(extra),
        )
        # every original body still there, in front of every new one
        offset = world_population.WIRE_HEADER_BYTES
        for length in generation.entry_bytes:
            self.assertIn(generation.pc[offset:offset + length], pc)
            offset += length
        for entry in extra:
            self.assertIn(entry, pc)

    def test_the_generation_itself_is_not_modified(self):
        generation = self._generation()
        before = (generation.pc, generation.frame, generation.actor_count,
                  generation.entry_bytes)
        world_population.append_census_entries(
            self.legacy, generation, (b"\x01\x02",),
        )
        self.assertEqual(
            before,
            (generation.pc, generation.frame, generation.actor_count,
             generation.entry_bytes),
        )

    def test_an_empty_or_non_bytes_entry_is_refused(self):
        generation = self._generation()
        for bad in (b"", "not bytes", None, bytearray(b"\x01")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    world_population.append_census_entries(
                        self.legacy, generation, (bad,),
                    )

    def test_a_generation_whose_entry_bytes_do_not_span_the_pc_is_refused(self):
        generation = self._generation()
        broken = replace(
            generation, entry_bytes=generation.entry_bytes[:-1],
        )
        with self.assertRaises(ValueError):
            world_population.append_census_entries(
                self.legacy, broken, (b"\x01\x02",),
            )

    def test_something_that_is_not_a_generation_is_refused(self):
        with self.assertRaises(ValueError):
            world_population.append_census_entries(
                self.legacy, object(), (b"\x01",),
            )

    def test_entries_must_be_a_sequence_not_a_bare_bytes_object(self):
        generation = self._generation()
        with self.assertRaises(ValueError):
            world_population.append_census_entries(
                self.legacy, generation, b"\x01\x02",
            )


if __name__ == "__main__":
    unittest.main()
