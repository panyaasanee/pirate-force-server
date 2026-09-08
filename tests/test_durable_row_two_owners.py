"""CORE-REQUEST `1808` items 1 and 2 -- the durable row has two owners.

LANE-A's letter (``20260908_1808_LANE-A-CORE-REQUEST-the-durable-row-has-two-
owners.md``, COO-DECISION ``20260908_1943`` making it the M-gate blocker)
measured one row assembled from two owners: ``x/y/z`` are what the CLIENT
reported in ``TargetPosVital``, while ``scene_id`` is the SERVER's belief,
which ``_gm_warp_resync_selected_scene`` relabels to a warp DESTINATION at
queue time and leaves wrong for the rest of the session when the client never
follows.  ``/warp 305`` the client ignores, plus one ordinary step, wrote
``(305, Port Royal's coordinates)`` into ``character_positions`` -- and since
PANYA ``1218`` login accepts the stored row wholesale, that row is permanent.

ITEM 2 IS WHY THIS FILE EXISTS AT ALL, NOT ONLY ITEM 1.  The letter's second
request was that the WRITER be tested: no test in this tree touched the
durable-write call site on the TargetPos path.  ``tests/test_lifecycle_
persist_position_gate.py`` feeds ``lifecycle.checkpoint`` a ``Position`` it
assembles itself, which cannot see a defect that lives in how runtime BUILDS
that Position.  So every test below drives the REAL dispatcher with a real
TargetPosVital frame and then reads the row back out of SQLite -- the client's
half of the row is a wire frame and the server's half is whatever runtime
decided, exactly as in production.

NONCLAIM: none of this is client-observable evidence (G5).  It is the wire/DB
layer alone -- what reaches ``character_positions`` after a decoded frame.
Whether a player sees the right ground under their feet after relogging is
GT-106's question and belongs to an attended round.
"""
import io
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm import login_scene_override  # noqa: E402
from pirateforce_foundation.gm.chat_command_action import (  # noqa: E402
    WARP_ACTION_LABEL,
)
from pirateforce_foundation.gm.warp_executor import WarpTarget  # noqa: E402
from pirateforce_foundation.gm.warp_target_record import (  # noqa: E402
    current_character_id,
    record_warp_target,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation.gm.warp_scene_persist import (  # noqa: E402
    login_would_accept,
)
from pirateforce_foundation.world_scene_travel import (  # noqa: E402
    is_position_persist_allowed,
    load_scene_registry,
)


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
WITHHELD_TOKEN = "DURABLE_ROW_WITHHELD_UNCONFIRMED_SCENE"
# The scene LANE-A's letter names: no ``ground`` block, so nothing downstream
# can refute a row that points at it, and the registry lets it persist.
UNREFUTABLE_SCENE_ID = 305
# The one the registry pins shut, used below to prove `durable=` can only
# ever subtract a write.
UNPERSISTED_SCENE_ID = 17
# Login DOES take this one back, so the gate lets its row through: the
# residual this round did not close, pinned rather than hidden.
LOGIN_ACCEPTED_SCENE_ID = 278


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class DurableRowTwoOwnersTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # Same pin, same reason, as test_gm_warp_position_confirmed.py: left
        # unpinned these resolve into gitignored `config/`, so a staged login
        # scene on the machine running the suite would turn a fact about this
        # fixture into a fact about that machine.
        env_pin = mock.patch.dict(gm_accounts.os.environ, {
            login_scene_override.ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_gm_login_scene.json"),
            login_scene_override.STANDALONE_ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_standalone_map.json"),
        })
        env_pin.start()
        self.addCleanup(env_pin.stop)
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
        field_mobs.load_roster()

    # ----- harness (the real dispatcher, no assembled Position anywhere) ---

    def _login_and_start(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
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
        return state

    def _target_pos_pc(self, x, y, z, heading=0.0, moving=1):
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.f32tag(x) + self.legacy.f32tag(y)
            + self.legacy.f32tag(z) + self.legacy.f32tag(heading)
            + self.legacy.u8tag(0x0B, moving)
            + self.legacy.u8tag(0x0B, 0)
        )

    def _report(self, state, x, y, z, heading=0.0):
        """One TargetPos through the real dispatcher; returns stderr."""
        captured = io.StringIO()
        with redirect_stderr(captured):
            state.dispatch(self.legacy.parse_outer(
                self._target_pos_pc(x, y, z, heading)
            ))
        return captured.getvalue()

    def _arm_a_cross_scene_warp(self, state, scene_id):
        """Park a target in `scene_id`, then queue the warp action.

        Mirrors ``chat_command_action``'s own order and reuses the same
        ``_dispatch_with_lanes`` seam ``test_gm_warp_position_confirmed.py``
        uses, so the arming half runs on the REAL ``dispatch()``: the resync
        that relabels the row and raises ``scene_label_is_server_guess`` is
        the production one, not a poked attribute.
        """
        x, y, z = self._memory(state)
        target = WarpTarget(scene_id, x + 1.0, y + 1.0, z)
        self.assertTrue(
            record_warp_target(state, target, current_character_id(state))
        )
        real = state._dispatch_with_lanes

        def _one_warp_action(parsed):
            state._dispatch_with_lanes = real
            return [(WARP_ACTION_LABEL, b"", b"", 0.0)]

        state._dispatch_with_lanes = _one_warp_action
        captured = io.StringIO()
        with redirect_stderr(captured):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_client_login_pc(state.token)
            ))
        return captured.getvalue()

    def _stored(self, state):
        position = self.store.get_character(
            state.foundation.selected.id
        ).position
        return (position.scene_id, position.x, position.y, position.z)

    def _memory(self, state):
        position = state.foundation.selected.position
        return (position.x, position.y, position.z)

    def _memory_scene(self, state):
        return state.foundation.selected.position.scene_id

    @staticmethod
    def _f32(value):
        return struct.unpack("<f", struct.pack("<f", value))[0]

    @staticmethod
    def _withheld_lines(text):
        return [
            line for line in text.splitlines()
            if line.startswith(WITHHELD_TOKEN)
        ]

    # ----- the control: an ordinary walk still persists --------------------

    def test_an_ordinary_step_still_writes_the_durable_row(self):
        """M1's own behaviour, unchanged.

        If this goes red the gate is not a gate, it is an outage: an ordinary
        player would stop keeping their position across logins.
        """
        state = self._login_and_start("dr_two_owners01")
        x, y, z = self._memory(state)
        moved = (x + 137.0, y - 42.0, z)
        err = self._report(state, *moved)

        scene_id, stored_x, stored_y, stored_z = self._stored(state)
        self.assertEqual(scene_id, 1)
        self.assertEqual(
            (stored_x, stored_y, stored_z),
            (self._f32(moved[0]), self._f32(moved[1]), self._f32(moved[2])),
        )
        self.assertEqual(self._withheld_lines(err), [])
        self.assertFalse(
            [e for e in state.events if e.startswith("durable_row_withheld")]
        )

    # ----- the defect the letter measured ---------------------------------

    def test_a_warp_the_client_ignores_writes_no_two_owner_row(self):
        """`/warp 305` + one step must not stamp 305 onto Port Royal's XYZ.

        The client keeps reporting from the scene it never left; the server's
        label says 305.  Before this round the stored row took both halves.
        """
        state = self._login_and_start("dr_two_owners02")
        before = self._stored(state)
        x, y, z = self._memory(state)
        self._arm_a_cross_scene_warp(state, UNREFUTABLE_SCENE_ID)
        self.assertEqual(self._memory_scene(state), UNREFUTABLE_SCENE_ID)

        # The client is still in Port Royal and says so, one step later.
        moved = (x + 3.0, y + 3.0, z)
        err = self._report(state, *moved)

        self.assertEqual(self._stored(state), before)
        self.assertEqual(
            self._withheld_lines(err),
            ["%s %d" % (WITHHELD_TOKEN, UNREFUTABLE_SCENE_ID)],
        )
        self.assertIn(
            "durable_row_withheld_unconfirmed_scene_%d" % UNREFUTABLE_SCENE_ID,
            state.events,
        )

    def test_the_withheld_frame_still_moves_the_in_memory_row(self):
        """Withholding the DURABLE row is not losing track of the player.

        The census, the travel gates and every reader in runtime.py read the
        in-memory position; a gate that froze it would break the live world
        to protect the stored one.
        """
        state = self._login_and_start("dr_two_owners03")
        x, y, z = self._memory(state)
        self._arm_a_cross_scene_warp(state, UNREFUTABLE_SCENE_ID)

        moved = (x + 3.0, y + 3.0, z)
        self._report(state, *moved)

        self.assertEqual(
            self._memory(state),
            (self._f32(moved[0]), self._f32(moved[1]), self._f32(moved[2])),
        )
        self.assertEqual(self._memory_scene(state), UNREFUTABLE_SCENE_ID)

    def test_the_withheld_frame_still_verifies_the_lease(self):
        """``store.save_position`` is this project's only stolen-lease signal.

        So the withheld branch asks the session for a NON-DURABLE write
        instead of skipping the call: ownership is still checked.  Measured
        by the argument the store actually receives, not by a comment.
        """
        state = self._login_and_start("dr_two_owners04")
        x, y, z = self._memory(state)
        self._arm_a_cross_scene_warp(state, UNREFUTABLE_SCENE_ID)

        seen = []
        real_save = self.store.save_position

        def _spy(sid, cid, pos, *, write_position=True):
            seen.append((pos.scene_id, write_position))
            return real_save(sid, cid, pos, write_position=write_position)

        with mock.patch.object(self.store, "save_position", _spy):
            self._report(state, x + 3.0, y + 3.0, z)

        self.assertEqual(seen, [(UNREFUTABLE_SCENE_ID, False)])

    def test_a_confirmed_warp_writes_again_on_the_next_step(self):
        """The cost, pinned so it cannot quietly grow.

        A warp the client DOES follow clears the guess on the frame that
        confirms it, and that frame runs the gate BEFORE the clear.  So the
        confirming step withholds and the NEXT one writes: one step, not one
        session.  A change that made this two steps -- or never -- would take
        the player's position away from them, and this test is what notices.
        """
        state = self._login_and_start("dr_two_owners05")
        x, y, z = self._memory(state)
        target_point = (x + 1.0, y + 1.0, z)
        self._arm_a_cross_scene_warp(state, UNREFUTABLE_SCENE_ID)
        before = self._stored(state)

        # The client lands exactly where the warp aimed: the confirm path.
        self._report(state, *target_point)
        self.assertEqual(self._stored(state), before)
        self.assertFalse(getattr(state, "scene_label_is_server_guess", False))

        second = (target_point[0] + 5.0, target_point[1], z)
        err = self._report(state, *second)
        self.assertEqual(self._withheld_lines(err), [])
        self.assertEqual(
            self._stored(state),
            (
                UNREFUTABLE_SCENE_ID,
                self._f32(second[0]), self._f32(second[1]),
                self._f32(second[2]),
            ),
        )

    # ----- the fence: a guess login would accept is still written ---------

    def test_the_gate_is_the_brick_not_the_guess(self):
        """The second half of the gate, and the residual it leaves.

        Withholding on the guess ALONE took five tests in this tree down:
        a rolled-back warp (whose label is restored but whose flag is not
        cleared) would have stopped that session persisting at all, and
        PANYA `1218` item 2 requires the M2 journey's row to name the sea.
        So the refusal is "the label is a guess AND login would not take
        that scene back" -- the row that bricks.

        THE RESIDUAL, MEASURED HERE ON PURPOSE: a warp to a scene login DOES
        accept, which the client never follows, still writes that scene with
        the departure's coordinates.  278's registry row is `sent_before=NO,
        return_ticket=REQUIRED`, so that character can log in and cannot walk
        home.  This test asserts the CURRENT behaviour so the day someone
        closes it, this is the line that says what changed.
        """
        registry = load_scene_registry()
        self.assertFalse(login_would_accept(UNREFUTABLE_SCENE_ID))
        self.assertTrue(login_would_accept(LOGIN_ACCEPTED_SCENE_ID))
        self.assertTrue(
            is_position_persist_allowed(LOGIN_ACCEPTED_SCENE_ID, registry)
        )

        state = self._login_and_start("dr_two_owners09")
        x, y, z = self._memory(state)
        self._arm_a_cross_scene_warp(state, LOGIN_ACCEPTED_SCENE_ID)
        self.assertTrue(getattr(state, "scene_label_is_server_guess", False))

        moved = (x + 3.0, y + 3.0, z)
        err = self._report(state, *moved)

        self.assertEqual(self._withheld_lines(err), [])
        self.assertEqual(
            self._stored(state),
            (
                LOGIN_ACCEPTED_SCENE_ID,
                self._f32(moved[0]), self._f32(moved[1]), self._f32(moved[2]),
            ),
        )

    # ----- the session double that predates the keyword -------------------

    def test_a_session_without_the_keyword_degrades_and_says_so(self):
        """Four test doubles in this tree spell ``checkpoint(self, position)``.

        A keyword-only parameter they do not carry is a TypeError, and a
        TypeError raised out of dispatch takes the connection down: v141's
        game listener has no ``except`` around ``state.dispatch``.  So the
        call boundary catches it and degrades to the in-memory move -- the
        same thing the login-override branch does -- but names the cost in
        its own event rather than reusing the one that means "the lease was
        checked".  Two different facts, two different event names.
        """
        state = self._login_and_start("dr_two_owners07")
        x, y, z = self._memory(state)
        self._arm_a_cross_scene_warp(state, UNREFUTABLE_SCENE_ID)
        before = self._stored(state)

        real = state.foundation.checkpoint

        def _keywordless(position):
            return real(position)

        state.foundation.checkpoint = _keywordless
        moved = (x + 3.0, y + 3.0, z)
        err = self._report(state, *moved)

        self.assertEqual(self._stored(state), before)
        self.assertIn(
            "durable_row_withheld_lease_unchecked_scene_%d"
            % UNREFUTABLE_SCENE_ID,
            state.events,
        )
        self.assertNotIn(
            "durable_row_withheld_unconfirmed_scene_%d"
            % UNREFUTABLE_SCENE_ID,
            state.events,
        )
        self.assertEqual(
            self._withheld_lines(err),
            ["%s %d" % (WITHHELD_TOKEN, UNREFUTABLE_SCENE_ID)],
        )
        self.assertEqual(
            self._memory(state),
            (self._f32(moved[0]), self._f32(moved[1]), self._f32(moved[2])),
        )

    def test_a_stolen_lease_still_gets_out_of_the_withheld_branch(self):
        """The ``except`` is TypeError, and it has to stay that way.

        ``store.save_position``'s ownership SELECT is the only stolen-lease
        signal this project has, and every other checkpoint call site in this
        file lets that raise out on purpose.  A wider ``except`` here would
        turn a hijacked session into a console line and a shrug -- measured:
        widening it to ``except Exception`` leaves this file's other tests
        green, so this is the one that notices.
        """
        state = self._login_and_start("dr_two_owners08")
        x, y, z = self._memory(state)
        self._arm_a_cross_scene_warp(state, UNREFUTABLE_SCENE_ID)

        def _stolen(sid, cid, pos, *, write_position=True):
            raise PermissionError("session does not own this character")

        with mock.patch.object(self.store, "save_position", _stolen):
            with self.assertRaises(PermissionError):
                self._report(state, x + 3.0, y + 3.0, z)

        self.assertFalse(
            [e for e in state.events if e.startswith("durable_row_withheld")]
        )

    # ----- `durable=` can only ever subtract a write ----------------------

    def test_the_registry_pin_still_wins_over_a_durable_caller(self):
        """``allowed = durable and is_position_persist_allowed(...)``.

        A caller asking for a durable write into a scene the registry pins
        shut must still write nothing.  Both halves are measured here rather
        than read off the source line: the registry's answer for 17 and 305,
        and what the store is asked for.
        """
        registry = load_scene_registry()
        self.assertFalse(is_position_persist_allowed(UNPERSISTED_SCENE_ID, registry))
        self.assertTrue(is_position_persist_allowed(UNREFUTABLE_SCENE_ID, registry))

        state = self._login_and_start("dr_two_owners06")
        x, y, z = self._memory(state)
        seen = []
        real_save = self.store.save_position

        def _spy(sid, cid, pos, *, write_position=True):
            seen.append(write_position)
            return real_save(sid, cid, pos, write_position=write_position)

        selected = state.foundation.selected
        state.foundation.selected = type(selected)(
            **{
                **{
                    field: getattr(selected, field)
                    for field in selected.__dataclass_fields__
                },
                "position": Position(
                    UNPERSISTED_SCENE_ID, selected.position.scene_seq,
                    x, y, z, selected.position.heading,
                ),
            }
        )
        with mock.patch.object(self.store, "save_position", _spy):
            state.foundation.checkpoint(
                Position(UNPERSISTED_SCENE_ID, 0, x + 1.0, y, z, 0.0),
            )
        self.assertEqual(seen, [False])


if __name__ == "__main__":
    unittest.main()
