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
from pirateforce_foundation import runtime  # noqa: E402
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

    def test_the_armed_line_reads_the_wire_count_off_the_queued_bytes(self):
        """pf-adversary (round ``ky8m6j``, D4): the console token must count
        what the collection about to go out SAYS, not what the module
        produced.  "eight entries were built" and "the frame says 116 bodies
        follow" are different claims, and only the second one is about the
        wire.
        """
        _state, actions, console = self._arrive_capturing(
            "sweep-wirecount", name_colour_sweep.SET_FACTION,
        )
        pc = self._labelled(actions, CENSUS_LABEL_PREFIX)[0][1]
        start = world_population.WIRE_COUNT_TAG_OFFSET + 1
        wire = int.from_bytes(pc[start:start + 2], "little")
        self.assertIn("NAME_COLOUR_SWEEP_ARMED", console)
        self.assertIn("wire=%d" % wire, console)

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


class SweepViewerAndEmptyWorldTests(unittest.TestCase):
    """The two runtime.py call sites LANE-B asked chief for on 2026-09-08.

    CORE-REQUEST ``pf_bridge notes_to_chief/20260908_0024``, relayed as
    COO-ORDER ``20260908_0042`` topic 2:

      1. the sweep is told WHO is looking (``viewer_identity=``), because the
         three "(viewer, mob) pair" rows of the ALL set cannot be built
         without it and the identity is a runtime fact the module cannot
         reach;
      2. the sets that must be read on an EMPTY square are composed alone,
         so the census the tester grades a nameboard against is the sweep and
         not Port Royal.

    WHY THE MODULE IS STOOD IN FOR HERE, AND WHAT THAT DOES AND DOES NOT
    PROVE.  When these tests were written both halves of the module -- the
    ``viewer_identity`` keyword and the ``ALL``/``ALL-NOID`` values
    themselves -- lived in LANE-B's own pull request and were NOT on this
    tree.  THAT IS NO LONGER TRUE: they reached main on 2026-09-08 while this
    branch waited, which is what two tests in this class measured when they
    went red.  The stand-ins are kept anyway, because a signature contract is
    what protects sets 1 and 2 on a tree where that module is reverted, and
    the real module is now pinned beside them
    (``test_the_module_on_this_tree_now_takes_the_keyword``,
    ``test_a_real_all_boot_composes_the_sweep_alone_on_this_tree``).  Wiring on this side is therefore
    proved against a stand-in whose SIGNATURE is the contract: that the call
    site passes the keyword when it exists, does not when it does not, and
    composes the collection the empty-world rule asks for.  It is NOT proof
    that any row LANE-B builds is correct, that the client draws it, or what
    colour a nameboard comes back -- those are the module's tests and an
    attended ticket, in that order.

    THE HARNESS IS BORROWED, NOT INHERITED.  Subclassing the wiring case
    would have re-run every one of its tests a second time under a new name,
    which inflates the suite and makes a failure report name the wrong class;
    copying the five methods would let two copies of the same boot drift.  So
    the methods are bound by name below and the class stays a plain TestCase.
    """

    setUp = NameColourSweepWiringTests.setUp
    tearDown = NameColourSweepWiringTests.tearDown
    _state = NameColourSweepWiringTests._state
    _target_pos_pc = NameColourSweepWiringTests._target_pos_pc
    _step = NameColourSweepWiringTests._step
    _labelled = NameColourSweepWiringTests._labelled
    _arrive_capturing = NameColourSweepWiringTests._arrive_capturing

    def _real_entries(self):
        """Valid entry bytes to hand back from a stand-in.

        Taken from the module's own set 1 so the bytes going into
        ``append_census_entries`` are the shape a real sweep produces -- a
        stand-in returning invented bodies would prove the merge accepts
        anything, which is the opposite of the point.
        """
        env = {name_colour_sweep.SWEEP_ENV: name_colour_sweep.SET_FACTION}
        entries = name_colour_sweep.sweep_entries(self.legacy, env)
        self.assertTrue(entries)
        return entries

    def _stub(self, entries, *, takes_viewer):
        """A stand-in for ``sweep_entries`` that records how it was called."""
        seen = []
        if takes_viewer:
            def stub(legacy, env=None, viewer_identity=None):
                seen.append(viewer_identity)
                return entries
        else:
            def stub(legacy, env=None):
                seen.append("not-offered")
                return entries
        return stub, seen

    def _boot(self, token, env_value, stub):
        console = io.StringIO()
        env = ({} if env_value is None
               else {name_colour_sweep.SWEEP_ENV: env_value})
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(
                name_colour_sweep, "sweep_entries", stub,
            ):
                with contextlib.redirect_stdout(console):
                    state = self._state(token)
                    actions = self._step(state)
        return state, actions, console.getvalue()

    # ----- item 1: who is looking -------------------------------------------

    def test_the_viewer_identity_passed_is_the_selected_characters_qword(self):
        """Not "a viewer was passed" -- WHICH viewer, read back off the
        session independently of the expression the call site uses.
        """
        entries = self._real_entries()
        stub, seen = self._stub(entries, takes_viewer=True)
        state, _actions, _console = self._boot(
            "sweep-viewer-1", name_colour_sweep.SET_FACTION, stub,
        )
        selected = state.foundation.selected
        expected = (
            (selected.identity_hi & 0xFFFFFFFF) << 32
            | (selected.identity_lo & 0xFFFFFFFF)
        )
        self.assertEqual(seen, [expected])
        self.assertNotEqual(expected, 0)

    def test_a_module_without_the_keyword_is_called_without_it(self):
        """THE REGRESSION THIS ROUND IS MOST LIKELY TO CAUSE.  The keyword
        reached main on 2026-09-08, so this is no longer a description of
        THIS tree -- it is the revert guard.  On any tree where that module
        is rolled back, a hard ``viewer_identity=`` would raise TypeError
        into the refusal path and hand every armed boot of set 1 and set 2
        an ordinary town instead of a sweep.  The stand-in is what keeps that
        branch executed; the real module is pinned by
        ``test_the_module_on_this_tree_now_takes_the_keyword``.
        """
        entries = self._real_entries()
        stub, seen = self._stub(entries, takes_viewer=False)
        _state, actions, console = self._boot(
            "sweep-viewer-2", name_colour_sweep.SET_FACTION, stub,
        )
        self.assertEqual(seen, ["not-offered"])
        self.assertNotIn("NAME_COLOUR_SWEEP_REFUSED", console)
        self.assertIn("NAME_COLOUR_SWEEP_ARMED", console)
        self.assertEqual(
            len(self._labelled(actions, CENSUS_LABEL_PREFIX)), 2,
        )

    def test_the_module_on_this_tree_now_takes_the_keyword(self):
        """THE DAY THE KEYWORD LANDED.  Until 2026-09-08 this test asserted
        the opposite -- that the module on this tree had no such parameter --
        and it was written to be the line that says the stand-in above has
        stopped describing reality.  It said exactly that when LANE-B's
        module reached main while this branch waited for review, so it is
        rewritten to measure what is true now rather than deleted.

        The revert direction is still covered:
        ``test_a_module_without_the_keyword_is_called_without_it`` boots a
        stand-in without the parameter and proves the call site drops the
        keyword instead of raising TypeError into the refusal path.
        """
        import inspect as _inspect
        self.assertIn(
            "viewer_identity",
            _inspect.signature(name_colour_sweep.sweep_entries).parameters,
        )

    def test_a_real_all_boot_composes_the_sweep_alone_on_this_tree(self):
        """The same claim as ``test_an_all_boot_composes_the_sweep_alone``,
        but with NO stand-in: the module that arms is the one on this tree,
        which now knows ``ALL``.

        This is the console line the attended boot of GT-288 set 3 is graded
        on -- ``census_actors=0`` is the token that says Port Royal is not on
        the wire underneath the sweep -- so it is pinned against the real
        module and not against a signature contract.
        """
        _state, actions, console = self._arrive_capturing(
            "sweep-empty-real-all", name_colour_sweep.SET_ALL,
        )
        self.assertIn("NAME_COLOUR_SWEEP_ARMED", console)
        self.assertIn("census_actors=0", console)
        self.assertNotIn("NAME_COLOUR_SWEEP_EMPTY_WORLD_REFUSED", console)
        self.assertNotIn("NAME_COLOUR_SWEEP_UNARMED", console)

    def test_the_call_site_is_reached_once_per_session_not_per_frame(self):
        """A signature read plus a keyword must not turn one call into two:
        the module's own dispatch contract is one compose per session.
        """
        entries = self._real_entries()
        stub, seen = self._stub(entries, takes_viewer=True)
        env = {name_colour_sweep.SWEEP_ENV: name_colour_sweep.SET_FACTION}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(
                name_colour_sweep, "sweep_entries", stub,
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    state = self._state("sweep-viewer-3")
                    self._step(state)
                    self._step(state, xyz=(11.0, 21.0, 31.0))
                    self._step(state, xyz=(12.0, 22.0, 32.0))
        self.assertEqual(len(seen), 1, seen)

    # ----- item 2: an empty square ------------------------------------------

    def test_an_all_boot_composes_the_sweep_alone(self):
        """The town is removed BY OMISSION (RE-092, replace-by-omission at
        COLLECTION scope), which is why the count in the collection about to
        go out has to equal the sweep and nothing else.  Read off the wire
        bytes, not off the module's return value.
        """
        entries = self._real_entries()
        for env_value in runtime.NAME_COLOUR_SWEEP_EMPTY_WORLD_SETS:
            with self.subTest(env_value=env_value):
                stub, _seen = self._stub(entries, takes_viewer=True)
                state, actions, console = self._boot(
                    f"sweep-empty-{env_value}", env_value, stub,
                )
                pc = self._labelled(actions, CENSUS_LABEL_PREFIX)[0][1]
                start = world_population.WIRE_COUNT_TAG_OFFSET + 1
                wire = int.from_bytes(pc[start:start + 2], "little")
                self.assertEqual(wire, len(entries))
                self.assertIn("census_actors=0 ", console)
                self.assertIn(f"wire={wire} ", console)
                # The rung handed back to every later recompose is the
                # CENSUS's, untouched: a zero here would be refused by
                # build_world_population on the next hit and RE-092 says a
                # compose failure empties the town for real.
                self.assertGreater(state.world_census_actor_count, 0)

    def test_set_one_and_set_two_still_ride_inside_the_town(self):
        """The other half of the same claim.  The empty square is for the
        sets that ask for it and for nothing else; sets 1 and 2 are read
        against the live NPCs on purpose (the ``N-BASE`` control).
        """
        entries = self._real_entries()
        for env_value in (
            name_colour_sweep.SET_FACTION,
            name_colour_sweep.SET_ACTOR_TYPE_AND_SKIN,
        ):
            with self.subTest(env_value=env_value):
                stub, _seen = self._stub(entries, takes_viewer=True)
                state, actions, console = self._boot(
                    f"sweep-town-{env_value}", env_value, stub,
                )
                pc = self._labelled(actions, CENSUS_LABEL_PREFIX)[0][1]
                start = world_population.WIRE_COUNT_TAG_OFFSET + 1
                wire = int.from_bytes(pc[start:start + 2], "little")
                self.assertEqual(
                    wire, state.world_census_actor_count + len(entries),
                )
                self.assertIn(
                    f"census_actors={state.world_census_actor_count} ",
                    console,
                )

    def test_the_console_number_is_the_rung_that_was_composed(self):
        """``census_actors=`` may not describe a census the wire does not
        carry.  Measured as the difference between the two boots rather than
        as a constant, so it stays true when the town's size changes.
        """
        entries = self._real_entries()
        stub, _seen = self._stub(entries, takes_viewer=True)
        state, _actions, town = self._boot(
            "sweep-line-town", name_colour_sweep.SET_FACTION, stub,
        )
        stub2, _seen2 = self._stub(entries, takes_viewer=True)
        _state2, _actions2, empty = self._boot(
            "sweep-line-empty",
            runtime.NAME_COLOUR_SWEEP_EMPTY_WORLD_SETS[0],
            stub2,
        )
        self.assertIn(
            f"census_actors={state.world_census_actor_count} ", town,
        )
        self.assertIn("census_actors=0 ", empty)
        self.assertNotIn("NAME_COLOUR_SWEEP_EMPTY_WORLD_REFUSED", town)
        self.assertNotIn("NAME_COLOUR_SWEEP_EMPTY_WORLD_REFUSED", empty)

    def test_an_empty_world_that_cannot_be_built_falls_back_to_the_town(self):
        """Fail closed, and SAY SO.  A sweep read against Port Royal is a bad
        result; a boot that silently pretends it emptied the square is worse,
        because the tester cannot tell the two apart on the console.
        """
        entries = self._real_entries()
        stub, _seen = self._stub(entries, takes_viewer=True)
        env = {
            name_colour_sweep.SWEEP_ENV:
                runtime.NAME_COLOUR_SWEEP_EMPTY_WORLD_SETS[0],
        }
        console = io.StringIO()
        real_make = self.legacy.make_runtime_remote_actors

        def refuse(bodies):
            if not bodies:
                raise RuntimeError("no empty collection for you")
            return real_make(bodies)

        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(
                name_colour_sweep, "sweep_entries", stub,
            ):
                with mock.patch.object(
                    self.legacy, "make_runtime_remote_actors", refuse,
                ):
                    with contextlib.redirect_stdout(console):
                        state = self._state("sweep-empty-refused")
                        actions = self._step(state)
        printed = console.getvalue()
        self.assertIn("NAME_COLOUR_SWEEP_EMPTY_WORLD_REFUSED", printed)
        self.assertIn(
            f"census_actors={state.world_census_actor_count} ", printed,
        )
        pc = self._labelled(actions, CENSUS_LABEL_PREFIX)[0][1]
        start = world_population.WIRE_COUNT_TAG_OFFSET + 1
        self.assertEqual(
            int.from_bytes(pc[start:start + 2], "little"),
            state.world_census_actor_count + len(entries),
        )
        self.assertTrue(any(
            event.startswith("name_colour_sweep_empty_world_refused_")
            for event in state.events
        ), list(state.events)[-6:])

    def test_an_unarmed_boot_never_asks_the_empty_world_question(self):
        """The predicate is read INSIDE the armed branch on purpose.  An
        ``ALL`` that arms NOTHING must empty nothing -- the town has to
        survive a boot the sweep refuses.

        Until 2026-09-08 the unarmed boot came for free: the module on this
        tree did not know ``ALL`` at all.  It knows it now, so the refusal is
        staged instead of inherited -- a stand-in that hands back no bodies,
        which is the same door an unknown value goes through.  Staging it is
        the point: the branch under test is chief's, and it must hold for
        every reason the module can decline, not only for the one that
        happened to be true on the day it was written.
        """
        stub, _seen = self._stub((), takes_viewer=False)
        _state, actions, console = self._boot(
            "sweep-empty-unarmed",
            runtime.NAME_COLOUR_SWEEP_EMPTY_WORLD_SETS[0],
            stub,
        )
        # MEASURED, and it is why this assertion is not the one that was
        # here before: a module that DECLINES a value it recognises prints
        # nothing at all -- `NAME_COLOUR_SWEEP_UNARMED` names the different
        # case of a value the module does not know (pinned by
        # `test_an_unknown_env_value_says_so_on_the_console`).  What both
        # cases owe the tester is the same, and it is what is asserted here:
        # the town is still on the wire.
        self.assertNotIn("NAME_COLOUR_SWEEP_ARMED", console)
        self.assertNotIn("NAME_COLOUR_SWEEP_EMPTY_WORLD_REFUSED", console)
        census = self._labelled(actions, CENSUS_LABEL_PREFIX)
        self.assertEqual(len(census), 2, [a[0] for a in actions])
        pc = census[0][1]
        start = world_population.WIRE_COUNT_TAG_OFFSET + 1
        self.assertGreater(
            int.from_bytes(pc[start:start + 2], "little"), 0,
        )


class SweepEmptyWorldPredicateTests(unittest.TestCase):
    """``runtime._sweep_wants_an_empty_world`` alone, without a boot."""

    def test_the_two_sets_the_owner_named_answer_true(self):
        for value in ("ALL", "ALL-NOID"):
            with self.subTest(value=value):
                self.assertTrue(runtime._sweep_wants_an_empty_world(
                    {name_colour_sweep.SWEEP_ENV: value},
                ))

    def test_every_other_value_answers_false(self):
        for value in ("", "1", "2", "all", "ALL ", "true", "ALL-NOID-X"):
            with self.subTest(value=value):
                self.assertFalse(runtime._sweep_wants_an_empty_world(
                    {name_colour_sweep.SWEEP_ENV: value},
                ))

    def test_an_absent_variable_answers_false(self):
        self.assertFalse(runtime._sweep_wants_an_empty_world({}))

    def test_the_module_owns_the_list_the_day_it_declares_one(self):
        """The two values are LANE-B's vocabulary, written here only because
        the set that needs them is in LANE-B's unmerged pull request.  When
        the module publishes its own tuple this file follows it, with no
        chief round in between -- measured, not promised.
        """
        with mock.patch.object(
            name_colour_sweep, "SWEEP_SETS_WANTING_AN_EMPTY_WORLD",
            ("ONLY-THIS-ONE",), create=True,
        ):
            self.assertTrue(runtime._sweep_wants_an_empty_world(
                {name_colour_sweep.SWEEP_ENV: "ONLY-THIS-ONE"},
            ))
            self.assertFalse(runtime._sweep_wants_an_empty_world(
                {name_colour_sweep.SWEEP_ENV: "ALL"},
            ))

    def test_an_environment_that_raises_answers_false(self):
        """Town-preserving on every failure: the predicate may not be the
        reason a boot loses its census.
        """
        class Hostile:
            def get(self, *_args, **_kwargs):
                raise RuntimeError("no environment here")

        self.assertFalse(runtime._sweep_wants_an_empty_world(Hostile()))

    def test_a_module_list_that_cannot_be_iterated_cannot_kill_dispatch(self):
        """pf-adversary round ``vx46m5`` D3, MEASURED before the fix: the
        membership test sat AFTER the ``try``, so a module publishing
        ``SWEEP_SETS_WANTING_AN_EMPTY_WORLD = None`` took ``tuple(names)``,
        ``dispatch()`` and the listener thread down with it -- and
        ``v141:7440`` has no ``except`` above that thread.

        The call site is ``if _sweep_wants_an_empty_world():`` with no guard
        of its own, so "this function does not raise" is the whole contract.
        """
        env = {name_colour_sweep.SWEEP_ENV: name_colour_sweep.SET_ALL}

        class Hostile:
            def __iter__(self):
                raise RuntimeError("no")

        for names in (None, 0, 3.5, Hostile(), object()):
            with self.subTest(names=type(names).__name__):
                with mock.patch.object(
                    name_colour_sweep,
                    "SWEEP_SETS_WANTING_AN_EMPTY_WORLD",
                    names,
                    create=True,
                ):
                    self.assertFalse(
                        runtime._sweep_wants_an_empty_world(env),
                    )

    def test_a_module_that_publishes_one_bare_name_is_read_as_one_name(self):
        """``("ALL-NOID")`` is a str, not a one-tuple -- the comma is the
        tuple.  Spelling it through ``tuple()`` would split it into eight
        letters and answer False FOR ITS OWN NAME, which is the silent
        version of the failure: the sweep composes on top of Port Royal,
        no refusal token is printed, and the attended nameboard is graded
        against a live NPC 23.6 units away (pf-adversary round ``vx46m5``
        D3).
        """
        with mock.patch.object(
            name_colour_sweep,
            "SWEEP_SETS_WANTING_AN_EMPTY_WORLD",
            "ALL-NOID",
            create=True,
        ):
            self.assertTrue(runtime._sweep_wants_an_empty_world(
                {name_colour_sweep.SWEEP_ENV: "ALL-NOID"},
            ))
            # ...and it is ONE name, not eight letters and not a prefix
            # match: the set that is not published stays False.
            self.assertFalse(runtime._sweep_wants_an_empty_world(
                {name_colour_sweep.SWEEP_ENV: "ALL"},
            ))
            self.assertFalse(runtime._sweep_wants_an_empty_world(
                {name_colour_sweep.SWEEP_ENV: "A"},
            ))


class EmptyRungContractTests(unittest.TestCase):
    """``world_population.empty_rung`` on its own.

    pf-adversary round ``vx46m5`` D8 measured that this function had NO
    direct test anywhere in the repo -- ``grep -rn empty_rung tests/ tools/``
    returned two comment lines -- and that four of its guards were
    mutation-invisible: the type guard, the frame-drift check, the
    header-length check and the ``indices=()`` reset could each be deleted
    with the whole wiring file still as green as it was.  An empty rung that
    carried the town's 108 ``indices`` would have shipped.
    """

    def setUp(self):
        self.legacy = _legacy()
        self.generation = world_population.build_world_population(
            self.legacy, (100.0, 200.0, 300.0), 3,
            scene_id=world_population.SCENE_ID,
        )
        self.assertGreater(self.generation.actor_count, 0)

    def test_the_rung_is_empty_in_every_member_that_names_a_body(self):
        rung = world_population.empty_rung(self.legacy, self.generation)
        self.assertEqual(rung.actor_count, 0)
        self.assertEqual(rung.indices, ())
        self.assertEqual(rung.actor_identities, ())
        self.assertEqual(len(rung.pc), world_population.WIRE_HEADER_BYTES)

    def test_the_original_generation_is_untouched(self):
        before = self.generation.actor_count
        indices = self.generation.indices
        world_population.empty_rung(self.legacy, self.generation)
        self.assertEqual(self.generation.actor_count, before)
        self.assertEqual(self.generation.indices, indices)

    def test_where_the_rung_was_built_is_carried_through(self):
        rung = world_population.empty_rung(self.legacy, self.generation)
        self.assertEqual(rung.scene_id, self.generation.scene_id)
        self.assertEqual(rung.anchor, self.generation.anchor)
        self.assertEqual(rung.undressable, self.generation.undressable)

    def test_something_that_is_not_a_generation_is_refused(self):
        for value in (None, 0, "generation", object(), {}):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    world_population.empty_rung(self.legacy, value)

    def test_an_encoder_whose_empty_collection_is_not_the_header_is_refused(
        self,
    ):
        """The rung exists to be WALKED by ``append_census_entries``, whose
        walk starts at ``WIRE_HEADER_BYTES``.  A longer empty collection
        fails that walk one call later with an error naming the append.
        """
        legacy = self.legacy
        real = legacy.make_runtime_remote_actors

        def longer(entries):
            pc, _frame = real(entries)
            pc = pc + b"\x00"
            # The frame is rebuilt FROM the longer pc on purpose: otherwise
            # the drift check above fires first and this test would pass
            # while measuring the wrong guard (it did, once).
            return pc, legacy.frame_pc(pc)

        with mock.patch.object(
            legacy, "make_runtime_remote_actors", longer,
        ):
            with self.assertRaises(ValueError) as caught:
                world_population.empty_rung(legacy, self.generation)
        self.assertIn("header", str(caught.exception))

    def test_a_frame_that_does_not_match_its_own_pc_is_refused(self):
        legacy = self.legacy
        real = legacy.make_runtime_remote_actors

        def drifted(entries):
            pc, frame = real(entries)
            return pc, frame + b"\x00"

        with mock.patch.object(
            legacy, "make_runtime_remote_actors", drifted,
        ):
            with self.assertRaises(ValueError) as caught:
                world_population.empty_rung(legacy, self.generation)
        self.assertIn("drift", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
