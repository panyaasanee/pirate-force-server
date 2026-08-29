"""CORE-REQUEST-GM-030 -- one DURABLE position write, one console token.

The write path this file guards is NOT new: on a flagless boot every
decodable TargetPos already reaches ``_checkpoint_exact_target``, which
calls ``foundation.checkpoint`` when the reported point differs from the
row.  What did not exist is visible evidence that a particular write is the
one the GM's warp was waiting for -- every TargetPos looked identical, so
GT-128 could not tell "the durable row caught up with the screen" apart
from "the tester happened to walk".

The contract this file now pins is the one the chief rewired after
pf-adversary measured three ways the first version printed a token that was
false.  In order:

1. a dispatch round that queued an action labelled ``WARP_ACTION_LABEL``
   arms ``gm_warp_position_pending`` and appends
   ``gm_warp_position_pending_armed``.  A second warp before any write
   appends ``gm_warp_position_pending_rearmed`` instead and does not arm a
   second time;
2. the FIRST TargetPos after arming disarms the pending lock and opens a
   confirm window that lives for exactly that one frame.  Nothing is
   printed and no event is appended at that moment -- opening the window is
   not a claim about anything;
3. the console token ``GM_WARP_POSITION_CONFIRMED`` (stderr, one line) and
   the event ``gm_warp_position_confirmed`` are emitted ONLY inside
   ``_checkpoint_exact_target``, and only when the reported point differs
   from the row AND ``world_scene_travel.is_position_persist_allowed`` says
   the character's scene may be written back -- i.e. only when a durable
   column write actually happened;
4. a warp frame that produced no durable write says so on the event trail
   instead: ``gm_warp_position_not_confirmed_scene_load_scenario`` on a
   scene-load boot, ``gm_warp_position_not_confirmed_no_durable_position_write``
   otherwise, and ``gm_warp_position_not_confirmed_character_changed`` when
   the character selected at TargetPos time is not the one the warp was
   armed for.  No console token in any of those cases -- silence would be
   indistinguishable from dead wiring, so the refusal is named, but it is
   named where a machine reads it, not where a person reads "confirmed".

So this file drives the REAL dispatcher, headless, with NO scenario objects
(the only boot shape GT-128 uses) and pins both halves: the token that must
appear on a real write, and the four ways it must NOT appear.

CORE-REQUEST-GM-029 is not wired, so no chat line can queue the warp action
yet.  The flag is therefore armed through the seam dispatch itself uses --
``_dispatch_with_lanes``, replaced for exactly one frame with one that
returns a single ``(WARP_ACTION_LABEL, pc, frame, 0.0)`` action.  That is
the same tuple shape ``make_gm_chat_command_action`` returns, so the arming
half is exercised on the real ``dispatch()`` and only the queueing half is
stood in for.

The TargetPos envelope builder is ``tests/test_move_authority_dispatch.py``'s
``_target_pos_pc``, kept in the tests for the reason that file gives: the
server never composes a client->server TargetPos.

NOT proven here: that a client moves.  RE-129 measured the client's own
ForcePos handler as ``mov al,1; ret 4`` -- this file is about who owns the
position in the database, nothing more.  That measurement is also why the
regression tests below exist at all: a client that ignores ForcePos reports
the OLD point on the first frame after a warp, which writes nothing.
"""
from __future__ import annotations

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
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.gm import (  # noqa: E402
    accounts as gm_accounts,
    login_scene_override,
)
from pirateforce_foundation.gm.chat_command_action import (  # noqa: E402
    WARP_ACTION_LABEL,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
CONSOLE_TOKEN = "GM_WARP_POSITION_CONFIRMED"
ARMED_EVENT = "gm_warp_position_pending_armed"
REARMED_EVENT = "gm_warp_position_pending_rearmed"
CONFIRMED_EVENT = "gm_warp_position_confirmed"
NOT_CONFIRMED_NO_WRITE = (
    "gm_warp_position_not_confirmed_no_durable_position_write"
)
NOT_CONFIRMED_SCENE_LOAD = (
    "gm_warp_position_not_confirmed_scene_load_scenario"
)

# The scene pf-adversary's D1 uses, and the exact standing point GT-106
# measured a character at inside it (the XYZ that came out of teardown
# written onto a scene_id=1 row, which is why the scene is pinned
# persist_position_allowed=False in scenarios/world_scene_registry_001.json).
UNPERSISTED_SCENE_ID = 17
UNPERSISTED_SCENE_POINT = (-149.0, -1250.3, 745.0)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class GmWarpPositionConfirmedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # Both login-scene override configs pinned inside this test's own
        # temp dir, at paths nothing writes.  Left unpinned they resolve to
        # the repo-relative defaults (`config/gm_login_scene.json`,
        # `config/gm_login_scene_standalone.json`), and `config/` is
        # gitignored -- so "this account has no staged login scene" would be
        # a fact about the machine running the suite rather than about this
        # fixture.  pf-adversary measured it against THIS file in
        # particular: one standalone map dropped into `config/` turns four
        # of its tests red, because an overridden login is a visit and a
        # visit never prints the token this file is named after.
        _login_scene_env_pin = mock.patch.dict(gm_accounts.os.environ, {
            login_scene_override.ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_gm_login_scene.json"),
            login_scene_override.STANDALONE_ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_standalone_map.json"),
        })
        _login_scene_env_pin.start()
        self.addCleanup(_login_scene_env_pin.stop)
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

    # ----- harness -------------------------------------------------------

    def _login_and_start(self, token, *, scene_load_scenario=None):
        """The flagless boot: no scenario arguments of any kind.

        ``scene_load_scenario`` is passed only by the lying-token guard test
        below, which needs the one boot shape that never checkpoints.
        """
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            scene_load_scenario=scene_load_scenario,
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
        """The exact singleton shape parse_v141_refresh_target_pos accepts."""
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
        """One TargetPos through the real dispatcher; returns captured stderr."""
        captured = io.StringIO()
        with redirect_stderr(captured):
            state.dispatch(self.legacy.parse_outer(
                self._target_pos_pc(x, y, z, heading)
            ))
        return captured.getvalue()

    def _arm_the_warp(self, state):
        """Queue one warp-labelled action from dispatch, for one frame only.

        Replaces the seam ``dispatch()`` already calls rather than reaching
        into the flag, so the arming branch under test is the production one:
        dispatch decides on the label of an action the lanes returned.
        """
        real = state._dispatch_with_lanes

        def _one_warp_action(parsed):
            state._dispatch_with_lanes = real
            return [(WARP_ACTION_LABEL, b"", b"", 0.0)]

        state._dispatch_with_lanes = _one_warp_action
        captured = io.StringIO()
        with redirect_stderr(captured):
            actions = state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_client_login_pc(state.token)
            ))
        self.assertEqual([action[0] for action in actions], [WARP_ACTION_LABEL])
        return captured.getvalue()

    @staticmethod
    def _f32(value):
        """What a float becomes after one round trip through the wire."""
        return struct.unpack("<f", struct.pack("<f", value))[0]

    def _row(self, state):
        character = self.store.get_character(state.foundation.selected.id)
        return (
            character.position.x, character.position.y, character.position.z,
        )

    def _row_scene(self, state):
        return self.store.get_character(
            state.foundation.selected.id
        ).position.scene_id

    def _origin(self, state):
        position = state.foundation.selected.position
        return position.x, position.y, position.z

    @staticmethod
    def _token_lines(text):
        return [line for line in text.splitlines() if line == CONSOLE_TOKEN]

    # ----- (a) the warp, then the first TargetPos -------------------------

    def test_a_flagless_boot_starts_with_the_lock_open(self):
        state = self._login_and_start("gmwarp01")
        self.assertFalse(state.gm_warp_position_pending)
        self.assertNotIn(ARMED_EVENT, state.events)

    def test_the_warp_action_arms_the_lock_without_printing_anything(self):
        """Armed at queue time; the token belongs to the WRITE, not to this."""
        state = self._login_and_start("gmwarp02")
        err = self._arm_the_warp(state)
        self.assertTrue(state.gm_warp_position_pending)
        self.assertEqual(state.events.count(ARMED_EVENT), 1)
        self.assertEqual(self._token_lines(err), [])
        self.assertNotIn(CONFIRMED_EVENT, state.events)

    def test_the_first_target_pos_after_a_warp_confirms_the_write(self):
        state = self._login_and_start("gmwarp03")
        x, y, z = self._origin(state)
        self._arm_the_warp(state)
        moved = (x + 4243.0, y + 1234.0, z)
        err = self._report(state, *moved)
        # Exactly one line, on stderr, and the lock is closed again.
        self.assertEqual(self._token_lines(err), [CONSOLE_TOKEN])
        self.assertEqual(state.events.count(CONFIRMED_EVENT), 1)
        self.assertFalse(state.gm_warp_position_pending)
        # A confirmed frame is never also a refused one.
        self.assertNotIn(NOT_CONFIRMED_NO_WRITE, state.events)
        # ... and the durable row is the new point, not the pre-warp one.
        self.assertEqual(
            self._row(state),
            (self._f32(moved[0]), self._f32(moved[1]), self._f32(moved[2])),
        )

    def test_the_token_is_ascii_and_goes_nowhere_near_stdout(self):
        """stdout is a tool contract: pf_runtimeres_death_headless_replay.

        That tool's --json artifact once gained a stray token line the same
        way (see lane_hooks/__init__.py); this pins the fix for this token.
        """
        from contextlib import redirect_stdout

        state = self._login_and_start("gmwarp04")
        x, y, z = self._origin(state)
        self._arm_the_warp(state)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            state.dispatch(self.legacy.parse_outer(
                self._target_pos_pc(x + 500.0, y + 500.0, z)
            ))
        self.assertIn(CONSOLE_TOKEN, err.getvalue())
        self.assertNotIn(CONSOLE_TOKEN, out.getvalue())
        self.assertTrue(err.getvalue().isascii(), repr(err.getvalue()))

    # ----- (b) an ordinary player ----------------------------------------

    def test_a_plain_player_walking_prints_no_token_at_all(self):
        state = self._login_and_start("gmwarp05")
        x, y, z = self._origin(state)
        err = self._report(state, x + 111.0, y + 222.0, z)
        self.assertEqual(self._token_lines(err), [])
        self.assertNotIn(CONFIRMED_EVENT, state.events)
        self.assertNotIn(ARMED_EVENT, state.events)
        # The write itself is untouched by this lane: the row still moved.
        self.assertEqual(
            self._row(state),
            (self._f32(x + 111.0), self._f32(y + 222.0), self._f32(z)),
        )

    def test_a_second_walk_still_prints_nothing(self):
        state = self._login_and_start("gmwarp06")
        x, y, z = self._origin(state)
        self._report(state, x + 111.0, y + 222.0, z)
        err = self._report(state, x + 333.0, y + 444.0, z)
        self.assertEqual(self._token_lines(err), [])
        self.assertNotIn(CONFIRMED_EVENT, state.events)

    # ----- (c) the lock is cleared by the write it confirmed --------------

    def test_the_second_target_pos_after_one_warp_prints_no_second_line(self):
        state = self._login_and_start("gmwarp07")
        x, y, z = self._origin(state)
        self._arm_the_warp(state)
        first = self._report(state, x + 4243.0, y + 1234.0, z)
        self.assertEqual(self._token_lines(first), [CONSOLE_TOKEN])
        second = self._report(state, x + 4300.0, y + 1300.0, z)
        self.assertEqual(self._token_lines(second), [])
        # One warp, one token, one event -- for the whole session.
        self.assertEqual(state.events.count(CONFIRMED_EVENT), 1)
        self.assertEqual(
            self._row(state),
            (self._f32(x + 4300.0), self._f32(y + 1300.0), self._f32(z)),
        )

    # ----- the lying-token guard -----------------------------------------

    def test_a_scene_load_boot_disarms_the_lock_instead_of_lying(self):
        """With a scene-load scenario the runtime never checkpoints.

        A flag left armed through that frame would fire the token later, on
        some unrelated frame, and say a warp landed when nothing was ever
        written.  Disarm on the decoded TargetPos, on events only, and name
        the reason: this boot shape cannot write a position at all.
        """
        from pirateforce_foundation.scene_load import load_scene_load_scenario

        scenario = load_scene_load_scenario(
            ROOT / "scenarios" / "scene2_fighting_fish_soldier.json"
        )
        state = self._login_and_start(
            "gmwarp08", scene_load_scenario=scenario,
        )
        x, y, z = self._origin(state)
        self._arm_the_warp(state)
        err = self._report(state, x + 4243.0, y + 1234.0, z)
        self.assertEqual(self._token_lines(err), [])
        self.assertNotIn(CONFIRMED_EVENT, state.events)
        self.assertIn(NOT_CONFIRMED_SCENE_LOAD, state.events)
        self.assertNotIn(NOT_CONFIRMED_NO_WRITE, state.events)
        self.assertFalse(state.gm_warp_position_pending)

    # ----- (D2) the client that ignores ForcePos --------------------------

    def test_a_warp_frame_that_repeats_the_row_confirms_nothing(self):
        """pf-adversary D2, the GT-128 case, in the shape it really arrives.

        RE-129 measured the client's ForcePos handler as ``mov al,1; ret 4``:
        it accepts the packet and moves nothing.  So the first TargetPos
        after a GM warp reports the point the row ALREADY holds, the
        candidate equals ``selected.position``, no checkpoint runs, and no
        column is written.  The frame must therefore say
        ``no_durable_position_write`` and print nothing.

        The second half is the defect itself: the tester, seeing the
        character has not moved, walks it by hand.  That later frame DOES
        write -- and the old wiring printed the token on it, which is
        precisely the confusion this token exists to prevent ("the durable
        row caught up with the warp" vs "the tester walked").  The confirm
        window is one frame wide, so it must stay silent.
        """
        state = self._login_and_start("gmwarp09")
        x, y, z = self._origin(state)
        before = self._row(state)
        self._arm_the_warp(state)

        # The warp's own frame: the client reports the OLD point.
        first = self._report(state, x, y, z)
        self.assertEqual(self._token_lines(first), [])
        self.assertNotIn(CONFIRMED_EVENT, state.events)
        self.assertEqual(state.events.count(NOT_CONFIRMED_NO_WRITE), 1)
        self.assertFalse(state.gm_warp_position_pending)
        self.assertFalse(state.gm_warp_confirm_window_open)
        self.assertEqual(self._row(state), before)

        # The tester walks by hand.  This one writes; it still says nothing.
        walked = (x + 812.0, y + 640.0, z)
        second = self._report(state, *walked)
        self.assertEqual(self._token_lines(second), [])
        self.assertNotIn(CONFIRMED_EVENT, state.events)
        self.assertEqual(state.events.count(NOT_CONFIRMED_NO_WRITE), 1)
        self.assertEqual(
            self._row(state),
            (self._f32(walked[0]), self._f32(walked[1]), self._f32(walked[2])),
        )

    def test_a_heading_only_second_frame_after_the_repeat_is_still_silent(self):
        """pf-adversary D2 variant: the tester turns instead of walking.

        A heading-only report differs from the row, so it DOES checkpoint --
        a durable write, on a frame that is not the warp's.  The token must
        still not appear, because the window closed on the frame before; a
        wiring that keyed on "a write happened while a warp was pending"
        rather than on the one frame would fire here.
        """
        state = self._login_and_start("gmwarp10")
        x, y, z = self._origin(state)
        self._arm_the_warp(state)

        first = self._report(state, x, y, z)
        self.assertEqual(self._token_lines(first), [])
        self.assertEqual(state.events.count(NOT_CONFIRMED_NO_WRITE), 1)

        second = self._report(state, x, y, z, heading=1.5)
        self.assertEqual(self._token_lines(second), [])
        self.assertNotIn(CONFIRMED_EVENT, state.events)
        # The x/y/z columns never moved across either frame ...
        self.assertEqual(
            self._row(state), (self._f32(x), self._f32(y), self._f32(z)),
        )
        # ... and the write that did happen was the heading alone.
        self.assertEqual(
            self.store.get_character(
                state.foundation.selected.id
            ).position.heading,
            self._f32(1.5),
        )

    # ----- (D1) the scene whose position is not persisted at all ----------

    def _stand_in_scene_17(self, state):
        """Put the SESSION's character where GT-106 measured one: scene 17.

        This is ``FoundationSession.checkpoint`` -- the same production call
        the world-travel lane makes when a character crosses into a new
        scene -- not a monkeypatch and not a rewritten dataclass.  The
        lifecycle, the persist gate and the store all run for real, and the
        column write is skipped by the gate itself, which is exactly the
        state GT-106 came out of: a character standing in scene 17 whose
        durable row still names where it was before.
        """
        state.foundation.checkpoint(
            Position(UNPERSISTED_SCENE_ID, 0, *UNPERSISTED_SCENE_POINT)
        )

    def test_the_registry_still_pins_scene_17_as_unpersisted(self):
        """The premise of the test below, asserted rather than assumed."""
        registry = world_scene_travel.load_scene_registry()
        self.assertFalse(
            world_scene_travel.is_position_persist_allowed(
                UNPERSISTED_SCENE_ID, registry,
            )
        )
        self.assertTrue(
            world_scene_travel.is_position_persist_allowed(1, registry)
        )

    def test_a_warp_inside_an_unpersisted_scene_confirms_nothing(self):
        """pf-adversary D1: ``checkpoint()`` returns cleanly, writing no row.

        In a scene pinned ``persist_position_allowed=False`` -- 17 today,
        which this project's own Columbus lane teleports into --
        ``lifecycle.checkpoint`` calls ``store.save_position`` with
        ``write_position=False``: ownership is still verified, the column is
        not touched, and nothing raises.  A token gated only on "the
        candidate differed from the row" printed there over an unchanged
        row.

        WHAT THIS PROVES: the whole runtime path for a character whose
        SESSION position is in scene 17 -- ``dispatch`` -> the confirm
        window -> ``_checkpoint_exact_target`` -> the real
        ``is_position_persist_allowed`` and the real store -- says
        ``no_durable_position_write`` and prints nothing.

        WHAT IT DOES NOT PROVE: that a character ever reaches scene 17 by a
        route this file exercised.  The boot harness cannot start one there
        (scene 17 is pinned ``login_entry_allowed=false``, so the login path
        refuses a stored row naming it), so the character is placed there
        through ``FoundationSession.checkpoint``, the seam the world-travel
        and Columbus lanes use.  Whether those lanes reach it correctly is
        their own tests' business, not this one's.
        """
        state = self._login_and_start("gmwarp11")
        before = self._row(state)
        before_scene = self._row_scene(state)
        self._stand_in_scene_17(state)
        # The session moved; the durable row deliberately did not.
        self.assertEqual(
            state.foundation.selected.position.scene_id, UNPERSISTED_SCENE_ID,
        )
        self.assertEqual(self._row(state), before)
        self.assertEqual(self._row_scene(state), before_scene)

        self._arm_the_warp(state)
        x, y, z = UNPERSISTED_SCENE_POINT
        err = self._report(state, x + 300.0, y + 300.0, z)

        self.assertEqual(self._token_lines(err), [])
        self.assertNotIn(CONFIRMED_EVENT, state.events)
        self.assertEqual(state.events.count(NOT_CONFIRMED_NO_WRITE), 1)
        self.assertFalse(state.gm_warp_position_pending)
        self.assertFalse(state.gm_warp_confirm_window_open)
        # No column moved: the row is the pre-scene-17 one, on its own scene.
        self.assertEqual(self._row(state), before)
        self.assertEqual(self._row_scene(state), before_scene)

    # ----- (D9) two warps, one write --------------------------------------

    def test_two_warps_before_one_write_arm_once_and_print_one_token(self):
        """pf-adversary D9: a second warp re-arms nothing and doubles nothing.

        A GM who types the command twice (or a queue that carries two warp
        actions before the client has reported once) must not leave the
        trail reading like one warp that armed twice, and must not buy a
        second token out of a single durable write.
        """
        state = self._login_and_start("gmwarp12")
        x, y, z = self._origin(state)
        self._arm_the_warp(state)
        self.assertEqual(state.events.count(ARMED_EVENT), 1)
        self.assertNotIn(REARMED_EVENT, state.events)

        second_arm = self._arm_the_warp(state)
        self.assertEqual(self._token_lines(second_arm), [])
        self.assertEqual(state.events.count(ARMED_EVENT), 1)
        self.assertEqual(state.events.count(REARMED_EVENT), 1)
        self.assertTrue(state.gm_warp_position_pending)

        moved = (x + 4243.0, y + 1234.0, z)
        err = self._report(state, *moved)
        self.assertEqual(self._token_lines(err), [CONSOLE_TOKEN])
        self.assertEqual(state.events.count(CONFIRMED_EVENT), 1)
        self.assertNotIn(NOT_CONFIRMED_NO_WRITE, state.events)
        self.assertFalse(state.gm_warp_position_pending)
        self.assertEqual(
            self._row(state),
            (self._f32(moved[0]), self._f32(moved[1]), self._f32(moved[2])),
        )


if __name__ == "__main__":
    unittest.main()
