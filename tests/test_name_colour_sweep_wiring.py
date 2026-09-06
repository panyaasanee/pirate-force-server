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
  * ARMED, the row is queued ONCE, on the same scene-arrival frame as the
    census, and its bytes are the module's own -- compared against an
    independently computed ``build_sweep_population``, not against a
    reconstruction of the dispatch's arithmetic.
  * The row is scheduled AFTER the census reapply (3.5s vs 3.0s), which is the
    one ordering decision chief made that LANE-B's letter left open.  Pinned
    here so a round that moves it has to come and change this line and read
    the reason in ``runtime.py`` first.
  * The sweep's actor identities are disjoint from the census's.  A collision
    would mean the row's dummies and real bg0001 mobs fight over the same
    actor slot in the client's collection.

NOT proven here, and not provable without a person at a screen: whether the
client draws any of these dummies at all, and what colour it paints their
names.  That is the whole reason RE-155 exists and it is an attended ticket,
not a test.  No count is written into this file's prose on purpose -- the two
armed sets have different sizes (set 1 measured 8 actors, set 2 six) and a
prose count is the kind of thing that goes stale silently; the assertions read
the count back from the module instead.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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

    def test_armed_set_1_queues_exactly_one_sweep_action(self):
        actions = self._arrive(
            "sweep-armed-1", name_colour_sweep.SET_FACTION,
        )
        sweep = self._labelled(actions, SWEEP_LABEL_PREFIX)
        self.assertEqual(len(sweep), 1, [a[0] for a in actions])

    def test_armed_set_2_queues_exactly_one_sweep_action(self):
        actions = self._arrive(
            "sweep-armed-2", name_colour_sweep.SET_ACTOR_TYPE_AND_SKIN,
        )
        sweep = self._labelled(actions, SWEEP_LABEL_PREFIX)
        self.assertEqual(len(sweep), 1, [a[0] for a in actions])

    def test_the_queued_sweep_bytes_are_the_modules_own(self):
        """Compared against an INDEPENDENT build, not against a rebuild of
        the dispatch's own arithmetic: the point is that the dispatcher ships
        what LANE-B's module composed, byte for byte.
        """
        env = {name_colour_sweep.SWEEP_ENV: name_colour_sweep.SET_FACTION}
        with mock.patch.dict(os.environ, env, clear=True):
            state = self._state("sweep-bytes")
            actions = self._step(state)
            expected = name_colour_sweep.build_sweep_population(self.legacy)
        self.assertIsNotNone(expected)
        expected_pc, expected_frame = expected
        label, pc, frame, _delay = self._labelled(
            actions, SWEEP_LABEL_PREFIX,
        )[0]
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_the_label_carries_the_actor_count_that_went_out(self):
        """v141 prints ``[G>] <label> (N bytes)`` per queued action at send
        time, so the label is what an attended tester reads on the console to
        tell a boot that composed six dummies from one that composed none.
        A label that disagrees with the row it names is worse than no label.
        """
        env = {name_colour_sweep.SWEEP_ENV: name_colour_sweep.SET_FACTION}
        with mock.patch.dict(os.environ, env, clear=True):
            state = self._state("sweep-label")
            actions = self._step(state)
            expected_count = len(name_colour_sweep.sweep_actors(self.legacy))
        label = self._labelled(actions, SWEEP_LABEL_PREFIX)[0][0]
        self.assertEqual(label, f"{SWEEP_LABEL_PREFIX}{expected_count}")

    def test_the_row_is_scheduled_after_the_census_reapply(self):
        """Chief's ordering decision, pinned.  The reason is in runtime.py at
        the wire: nothing in this house has measured what a second
        RuntimeRemoteActors frame does to actors the first did not mention,
        and the row exists to be READ off a screen, so it goes out after the
        census has finished repeating itself.
        """
        actions = self._arrive(
            "sweep-order", name_colour_sweep.SET_FACTION,
        )
        census_delays = [
            a[3] for a in self._labelled(actions, CENSUS_LABEL_PREFIX)
        ]
        sweep_delay = self._labelled(actions, SWEEP_LABEL_PREFIX)[0][3]
        self.assertEqual(
            sorted(census_delays),
            [0.0, world_population.INITIAL_REAPPLY_MS / 1000.0],
        )
        self.assertGreater(sweep_delay, max(census_delays))
        self.assertEqual(
            sweep_delay,
            (world_population.INITIAL_REAPPLY_MS + 500) / 1000.0,
        )

    def test_the_sweep_identities_do_not_collide_with_the_census(self):
        """A shared actor identity would put a dummy and a real bg0001 mob in
        the same slot of the client's collection, and whichever frame arrived
        second would win -- which is exactly the kind of result that reads as
        "the colour experiment did nothing".
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

    def test_the_row_is_queued_once_per_session_not_once_per_frame(self):
        """The census branch is one-shot per session (``world_census_sent``
        latches).  The sweep is inside it, so it inherits that -- but the
        inheritance is the claim, and a future edit that moves the block one
        indent level out would silently re-send six dummies on every step.
        """
        env = {name_colour_sweep.SWEEP_ENV: name_colour_sweep.SET_FACTION}
        with mock.patch.dict(os.environ, env, clear=True):
            state = self._state("sweep-once")
            first = self._step(state)
            second = self._step(state, xyz=(11.0, 21.0, 31.0))
            third = self._step(state, xyz=(12.0, 22.0, 32.0))
        self.assertEqual(len(self._labelled(first, SWEEP_LABEL_PREFIX)), 1)
        self.assertEqual(self._labelled(second, SWEEP_LABEL_PREFIX), [])
        self.assertEqual(self._labelled(third, SWEEP_LABEL_PREFIX), [])


if __name__ == "__main__":
    unittest.main()
