"""The scene-edge seam LANE-DB asked chief for (`20260907_2032`).

WHAT THIS FILE PINS, and equally what it refuses to pin.  It pins that the
seam fires on the scene the character LEFT, that it is bounded by confirmed
scene CHANGES rather than by frames, and that every way it can fail costs an
event and never the connection.  It does NOT pin that `GT-301` passes, that
the panel reads a different number, or that this seam sees every exit -- the
seam's own docstring names the exits it cannot see (a warp that never
confirms, a logout) and a test claiming otherwise would be the overclaim
that letter warned about.

The console token itself is read back off `sys.stderr`, not asserted from
the composer: an operator greps the console, so a test that only asked the
composer what it would have said would pass on a seam that never printed.
"""

import io
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_scene_exit_vitals as exitv  # noqa: E402,E501
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402,E501
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


class SceneExitVitalsSeamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.store = SQLiteStore(
            Path(self.tmp.name) / "seam.sqlite3", ROOT / "migrations")
        self.store.migrate()
        default = Position(
            1, 0, self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, default,
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.projector = LegacyProjector(self.legacy)

    def tearDown(self):
        self.tmp.cleanup()

    def booted_state(self):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector, None)
        state = state_type("scene-exit-seam")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(state.foundation.account_id)[0]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)))
        return state

    def confirm(self, state, scene_id, why="position_report"):
        """Drive the field the seam hangs off and capture the console.

        Returns `(printed_lines, new_events)`.
        """
        before = len(state.events)
        buffer = io.StringIO()
        with unittest.mock.patch.object(sys, "stderr", buffer):
            state._note_client_confirmed_scene(scene_id, why)
        lines = [line for line in buffer.getvalue().splitlines() if line]
        return lines, state.events[before:]

    def seed_primary_pair(self, state, current=70, maximum=100):
        self.store.write_typed_attributes(
            state.foundation.selected.id,
            {"hp_current": current, "hp_max": maximum},
        )

    # ---- the property the whole request turns on -------------------------

    def test_the_token_names_the_scene_that_was_left_not_the_one_entered(self):
        """The letter's one hard requirement, and the only reason this seam
        sits on this field rather than on any of the three that relabel the
        row before the client has moved."""
        state = self.booted_state()
        self.seed_primary_pair(state)
        self.confirm(state, 126)            # arrive: nothing left yet
        lines, events = self.confirm(state, 3)
        self.assertEqual(len(lines), 1, lines)
        line = lines[0]
        self.assertTrue(
            line.startswith(exitv.SCENE_EXIT_VITALS_CONSOLE_TOKEN), line)
        self.assertIn("scene=126", line)
        self.assertNotIn("scene=3", line)
        self.assertIn("restated=x3=70,x4=100", line)
        self.assertIn("boat_rows_unstated=x52/x53", line)
        self.assertIn(
            "scene_exit_vitals_stated_126_to_3_position_report", events)

    def test_the_first_confirmation_of_a_session_states_nothing(self):
        """`None` is not a scene that was left.  A restate here would be a
        login line wearing an exit's name."""
        state = self.booted_state()
        self.seed_primary_pair(state)
        lines, events = self.confirm(state, 126)
        self.assertEqual(lines, [])
        self.assertEqual(
            [e for e in events if e.startswith("scene_exit_vitals")], [])
        self.assertEqual(state.client_confirmed_scene, 126)

    def test_scene_zero_is_a_scene_and_is_not_refused_as_falsey(self):
        """Refused BY TYPE, not by truthiness: a `if not left_scene` guard
        would have dropped every exit from scene 0."""
        state = self.booted_state()
        self.seed_primary_pair(state)
        state.client_confirmed_scene = 0
        lines, events = self.confirm(state, 126)
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("scene=0", lines[0])
        self.assertIn(
            "scene_exit_vitals_stated_0_to_126_position_report", events)

    # ---- bounded by confirmed changes, not by frames ---------------------

    def test_re_confirming_the_same_scene_reads_nothing(self):
        """The early return above the call is what keeps this off the
        per-frame path; if it ever moves, this goes red rather than the
        database quietly taking a read per position report."""
        state = self.booted_state()
        self.seed_primary_pair(state)
        self.confirm(state, 126)
        self.confirm(state, 3)
        reads = []
        real = self.store.read_typed_attributes
        with unittest.mock.patch.object(
                type(self.store), "read_typed_attributes",
                lambda s, cid: reads.append(cid) or real(cid)):
            for _ in range(5):
                lines, _events = self.confirm(state, 3)
                self.assertEqual(lines, [])
        self.assertEqual(reads, [])

    # ---- every refusal is named, and none of them raises -----------------

    def test_an_unseeded_row_shouts_a_refusal_rather_than_inventing_hp(self):
        """MEASURED WHILE WRITING THIS, and it is the more useful half of the
        case: a character created on a flagless boot arrives here ALREADY
        seeded -- `LOGIN_VITALS from_row level=1 hp=100/100` on this very
        harness -- so the token an operator will actually see on an ordinary
        exit is the STATED one, not the refusal.  The refusal is still real
        and still has to be pinned; reaching it takes NULLing the columns
        under the seam, which is what a pre-`006` row looks like.
        """
        state = self.booted_state()
        with self.store.connect() as connection:
            connection.execute(
                "UPDATE characters SET hp_current = NULL, hp_max = NULL "
                "WHERE id = ?", (state.foundation.selected.id,))
        self.confirm(state, 126)
        lines, events = self.confirm(state, 3)
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith("!! "), lines[0])
        self.assertIn("restated=none", lines[0])
        self.assertIn(exitv.REASON_ROW_UNSEEDED, lines[0])
        self.assertIn(
            "scene_exit_vitals_refused_126_to_3_position_report", events)

    def test_a_resolver_that_raises_costs_an_event_and_not_the_connection(self):
        """v141's game listener has no `except` around `state.dispatch`, so
        an escape here would unwind the listener thread mid-scene-change.
        `KeyError` is the resolver's own documented raise."""
        state = self.booted_state()
        self.seed_primary_pair(state)
        self.confirm(state, 126)
        with unittest.mock.patch.object(
                exitv, "resolve_for_scene_exit",
                side_effect=KeyError("no such character")):
            lines, events = self.confirm(state, 3)
        self.assertEqual(lines, [])
        self.assertIn("scene_exit_vitals_raised_KeyError_126", events)
        # The field still moved: a restate may never be the reason the
        # session forgets where the client is.
        self.assertEqual(state.client_confirmed_scene, 3)
        self.assertIn("client_confirmed_scene_3_position_report", events)

    def test_a_session_with_no_store_is_named_not_crashed(self):
        state = self.booted_state()
        self.confirm(state, 126)
        with unittest.mock.patch.object(
                state.foundation.lifecycle, "store", None):
            lines, events = self.confirm(state, 3)
        self.assertEqual(lines, [])
        self.assertIn("scene_exit_vitals_no_store_126_to_3", events)

    def test_a_session_with_no_selected_character_is_named_not_crashed(self):
        """Reached through the same door `current_character_id` guards: no
        character selected answers `None`, and `None` is not an id."""
        state = self.booted_state()
        self.confirm(state, 126)
        with unittest.mock.patch.object(state.foundation, "selected", None):
            lines, events = self.confirm(state, 3)
        self.assertEqual(lines, [])
        self.assertIn("scene_exit_vitals_no_character_126_to_3", events)

    def test_the_console_line_is_ascii_and_one_line(self):
        """The bridge console is cp874; a character outside it kills the tool
        that reads the log this token exists to be grepped out of."""
        state = self.booted_state()
        self.seed_primary_pair(state)
        self.confirm(state, 126)
        lines, _events = self.confirm(state, 3)
        self.assertEqual(len(lines), 1)
        lines[0].encode("ascii")


if __name__ == "__main__":
    unittest.main()
