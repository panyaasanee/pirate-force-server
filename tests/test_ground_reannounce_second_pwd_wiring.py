"""The ground re-announce is wired to the reply the ATTENDED build sends.

LANE-B built `mob_drop_presence.reannounce_ground` and asked chief for one
line in `runtime.py` (`GROUND_REANNOUNCE_WIRING`), naming "the block that
calls ... `make_proactive_second_password_ok`".  Both such blocks sit behind
`second_password_mode == "bypass"`, and the attended build must boot
`required` -- `--second-password-mode bypass` switches the census off on all
13 maps (`runtime.py` `world_census_enabled`, and LANE-GM's letter
`pf_bridge/notes_to_chief/20260902_1604_LANE-GM-TO-CHIEF-gt192-*`).  A line
pasted where the ask literally pointed would have been dead code on every
boot Panya can run, and `GT-242`'s own RECHECK rule reads zero
`GROUND_REANNOUNCE_AFTER_SECOND_PWD` lines as "old build", not as a passing
negative control -- so the round would have been spent for nothing.

The reply IS sent on a `required` boot, by INHERITANCE, which is why no grep
of `runtime.py` finds the vital: `PersistentGameSessionState` extends
`legacy.GameSessionState`, and `super().dispatch(parsed)` reaches
`pf_login_game_server_v141.py:3864-3867`.  ka1-A's R309 log records both
halves on a no-flag boot.

These tests exist so the wire is proven by BEHAVIOUR rather than by reading
the source for a call: a source-text assertion cannot tell a composed frame
from an appended one, and D6 of this round's pf-adversary report named that
exact false green.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_drop_presence
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: The exact V102 runtime capture v141's own self-test dispatches
#: (`pf_login_game_server_v141.py:5121`).  Pinned as bytes rather than
#: rebuilt, so a change to the composer cannot quietly change the request
#: this test drives.
CHECK_SECOND_PWD_REQUEST_PC = bytes.fromhex(
    "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 "
    "98 4B 0B 00 08 00 19 00 00 00 00 44 20 00 00 00 "
    "37 44 30 31 34 45 35 34 31 41 46 41 41 34 33 32 "
    "36 37 43 41 38 30 42 43 43 42 43 33 46 44 36 42"
)

#: An empty runtime poll -- the shape that carries no nested vital at all.
EMPTY_RUNTIME_PC = bytes.fromhex("12 6F 6E 14 00 00 00 00 08 00 0B 00")

APPEND_EVENT_PREFIX = "ground_reannounce_after_second_pwd_appended_"


class GroundReannounceAfterSecondPasswordTests(unittest.TestCase):
    """Drive the real dispatcher headless, on a `required` boot, no flags."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(Path(self.tmp.name) / "state.sqlite3",
                                 ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        default = Position(
            1, 0, self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, default,
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def _state(self, mode="required"):
        """A logged-in, started session with NO scenario flags of any kind."""
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            second_password_mode=mode,
        )
        state = state_type("gt242")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()))
        created = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC))
        self.assertEqual(created[0][0], "FOUNDATION_CREATE_COMMITTED")
        character = self.store.list_characters(state.foundation.account_id)[0]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)))
        return state

    def _append_events(self, state):
        return [event for event in state.events
                if event.startswith(APPEND_EVENT_PREFIX)]

    def test_the_reply_this_wire_hangs_off_is_sent_on_a_required_boot(self):
        """The premise, measured -- not assumed from a grep of runtime.py.

        If this ever goes red, the wire below is dead code and `GT-242`
        cannot be booted; that is the finding, not a broken test.
        """
        state = self._state(mode="required")
        actions = state.dispatch(
            self.legacy.parse_outer(CHECK_SECOND_PWD_REQUEST_PC))
        labels = [action[0] for action in actions]
        self.assertIn("V110_CHECK_SECOND_PASSWORD_OK", labels)
        reply = actions[labels.index("V110_CHECK_SECOND_PASSWORD_OK")]
        self.assertEqual((len(reply[1]), len(reply[2])), (34, 44))
        expected_pc, expected_frame = \
            self.legacy.make_check_second_password_success()
        self.assertEqual((reply[1], reply[2]), (expected_pc, expected_frame))

    def test_the_reannounce_runs_on_that_reply_and_the_reply_comes_first(self):
        """Order is load-bearing: the client must see OK, then the truth."""
        state = self._state(mode="required")
        actions = state.dispatch(
            self.legacy.parse_outer(CHECK_SECOND_PWD_REQUEST_PC))
        events = self._append_events(state)
        self.assertEqual(len(events), 1, state.events[-6:])

        labels = [action[0] for action in actions]
        appended = int(events[0][len(APPEND_EVENT_PREFIX):])
        self.assertEqual(appended, len(actions) - labels.index(
            "V110_CHECK_SECOND_PASSWORD_OK") - 1)
        # Whatever the re-announce contributed sits AFTER the reply, never
        # before it and never in place of it.
        self.assertLess(labels.index("V110_CHECK_SECOND_PASSWORD_OK"),
                        len(actions))

    def test_an_empty_floor_appends_nothing_but_still_records_the_call(self):
        """`items=0` (checked, bare) must stay distinguishable from `no wire`.

        This is the pair `GROUND_REANNOUNCE_TOKEN`'s docstring asks for, and
        it is why the event carries a COUNT rather than being a bare name.
        """
        state = self._state(mode="required")
        state.dispatch(self.legacy.parse_outer(CHECK_SECOND_PWD_REQUEST_PC))
        events = self._append_events(state)
        self.assertEqual(events, ["%s0" % APPEND_EVENT_PREFIX])

    def test_no_other_inbound_frame_triggers_a_reannounce(self):
        """The guard, not the paste location, is what keeps this off a cadence.

        Every non-ChooseNPC vital reaches the same branch, so an UNGUARDED
        extend there would resend the whole floor on every inbound frame --
        the standing cadence resend recorded at
        `WITHDRAWN_DROP_PRESENCE_RESEND_ON_MOVEMENT_WIRING` as refused by COO
        on 2026-08-30T17:42.  A mutant that drops the `nested_id` guard turns
        this test red.
        """
        state = self._state(mode="required")
        for _ in range(5):
            state.dispatch(self.legacy.parse_outer(EMPTY_RUNTIME_PC))
        self.assertEqual(self._append_events(state), [])

        state.dispatch(self.legacy.parse_outer(CHECK_SECOND_PWD_REQUEST_PC))
        self.assertEqual(len(self._append_events(state)), 1)

        for _ in range(5):
            state.dispatch(self.legacy.parse_outer(EMPTY_RUNTIME_PC))
        self.assertEqual(len(self._append_events(state)), 1)

    def test_the_wire_is_present_on_a_bypass_boot_too_and_stays_guarded(self):
        """`bypass` is not the attended build, but the wire must not depend on
        which mode is running -- the guard is the vital, not the mode."""
        state = self._state(mode="bypass")
        for _ in range(3):
            state.dispatch(self.legacy.parse_outer(EMPTY_RUNTIME_PC))
        self.assertEqual(self._append_events(state), [])


class TheReannounceFunctionIsTheOneLaneBShippedTests(unittest.TestCase):
    """Guards on the contract this call site relies on, so a change to
    `mob_drop_presence` that breaks the call site fails HERE rather than in
    an attended round."""

    def test_reannounce_ground_never_raises_and_always_returns_a_tuple(self):
        for cell in (None, object(), 0, "", [], {"scene": 1}):
            result = mob_drop_presence.reannounce_ground(cell, None)
            self.assertIsInstance(result, tuple)
            self.assertEqual(result, ())

    def test_the_two_console_tokens_stay_distinct(self):
        """`items=0` and a refusal must never grep as the same line -- the
        `GT-242` RECHECK criterion reads the absence of one as `old build`."""
        checked = mob_drop_presence.GROUND_REANNOUNCE_TOKEN
        refused = mob_drop_presence.GROUND_REANNOUNCE_REFUSED_TOKEN
        self.assertNotEqual(checked, refused)
        self.assertTrue(refused.startswith(checked))
        # A grep for the plain token would match the refusal too, so anything
        # reading the console must anchor on the trailing space or the suffix.
        self.assertIn(checked, refused)

    def test_every_byte_of_both_tokens_is_ascii(self):
        """The bridge console is cp874; a token outside it kills the report."""
        for token in (mob_drop_presence.GROUND_REANNOUNCE_TOKEN,
                      mob_drop_presence.GROUND_REANNOUNCE_REFUSED_TOKEN,
                      APPEND_EVENT_PREFIX):
            token.encode("ascii")


if __name__ == "__main__":
    unittest.main()
