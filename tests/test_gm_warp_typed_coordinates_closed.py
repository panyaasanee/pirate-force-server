"""No `/warp` carrying TYPED COORDINATES may leave one byte, in any shape.

WHY THIS FILE EXISTS
--------------------
`COO-DECISION 2026-09-04T20:45+07:00` item 1 (pf_bridge/notes_to_chief/
20260904_2045_COO-DECISION-warp-with-coords-must-close-for-real-745-R2-
continues-LANE-GM.md) corrects the wording of `1848` item 2(b) and restores
what `1744` item 3 and NOW.md's `/warp <n> <x> <y>` line actually mean:

    refuse BEFORE composing any frame -- a console line -- ZERO BYTES on the
    wire.

It was ordered because this lane's own adversary pass (round `741zlx`,
finding 10, MEASURED, reported to COO in `1930`) found the previous closure
was true of one shape and false of the other.  `WARP_SAME_SCENE_FORCE_POS_
AUTHORIZED` shuts the SAME-SCENE ForcePos half; a CROSS-SCENE
`/warp 2 100 200` is routed one branch earlier and COMPOSED AND SENT a real
73-byte TeleportVital carrying the coordinates the GM typed.  What `#745`
withdrew on that path was the durable row write, not the frame.  R306
measured a coordinate-bearing warp closing the owner's client with
`ErrorData=28317`, so a frame still going out on that path is a live wire.

WHAT IS PINNED HERE, AND WHY IT IS PINNED THIS WAY
--------------------------------------------------
Three shapes, because three is how many ways `_warp_action` can route a
coordinate-bearing command, and finding 10 is what a per-branch closure costs:

    1. same scene    `/warp 1 100 200` standing in scene 1
    2. cross scene   `/warp <other> 100 200`, live TeleportVital authorized
    3. cross scene   the same text with `WARP_CROSS_SCENE_LIVE_TELEPORT_
                     AUTHORIZED` off, i.e. the staging fall-through

Each is asserted on FOUR leavings, not one, because "no bytes" alone was the
assertion that let finding 10 hide: no action, no parked target, no staged
login-scene entry, no scene-persist event.

THE GUARD IS PROVEN LOAD-BEARING, not merely present.  `TheGuardIsWhatDoesIt
Tests` flips `WARP_TYPED_COORDINATES_AUTHORIZED` to True and shows shape 2
composing a real frame again in the same breath -- so if the guard were
deleted, the shipped-flag tests below go red instead of quietly passing for
a second reason.  That is this round's mutant, written as a test rather than
run by hand, so the next round inherits it.

WHAT IS NOT CLAIMED
-------------------
Nothing here says a client did or did not receive anything, and nothing here
says the coordinate warp is FIXED.  It is CLOSED: the RE result that diffs a
real coordinate-bearing capture is what would reopen it.  Bare `/warp <n>`
is untouched by every test in this file -- R306 passed it five times and
Panya has ruled it untouchable -- and `TheBareWarpIsUntouchedTests` pins
exactly that, because a closure that quietly widened would be worse than the
hole it closed.
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import login_scene_admission  # noqa: E402
from pirateforce_foundation.gm import warp_executor  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


def make_chat_payload(message: str, speaker: str = "") -> bytes:
    """0xAC52 payload in the GT-006/GT-009 measured shape."""
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


class FakePosition:
    def __init__(self, scene_id=1, x=10.0, y=20.0, z=30.0):
        self.scene_id = scene_id
        self.scene_seq = 0
        self.x = x
        self.y = y
        self.z = z


class FakeSelected:
    def __init__(self, position=None):
        self.position = position
        self.id = 4242


class FakeFoundation:
    def __init__(self, selected=None):
        self.selected = selected


class FakeSession:
    def __init__(self, token="GM_ONE", position=None):
        self.token = token
        self.events = []
        self.foundation = FakeFoundation(FakeSelected(position))


class _Case(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"
    CURRENT_SCENE = 1

    def setUp(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.config_path = self.tmp / "gm_accounts.json"
        self.config_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT]}), encoding="utf-8"
        )
        self.log_path = self.tmp / "capture" / "gm_command_log.ndjson"
        self.login_scene_config_path = self.tmp / "config" / "gm_login_scene.json"
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def act(self, session, text):
        """Drive the real dispatch, capturing whatever it writes to stderr."""
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            action = chat_command_action.make_gm_chat_command_action(
                session,
                make_chat_payload(text),
                self.legacy,
                config_path=str(self.config_path),
                log_path=str(self.log_path),
                login_scene_config_path=str(self.login_scene_config_path),
            )
        return action, buffer.getvalue()

    def a_different_marker_backed_scene(self) -> int:
        """A scene id the live cross-scene teleport half would really take.

        Read from the live predicate rather than typed as a constant: lane A
        adds registry rows most days, and a hardcoded id would one morning
        stop being the shape this file means to test while staying green.
        """
        for scene in login_scene_admission.stageable_scene_ids():
            if scene != self.CURRENT_SCENE:
                return scene
        raise AssertionError("no second stageable scene -- rewrite this helper")

    def session_in_scene(self) -> FakeSession:
        return FakeSession(position=FakePosition(scene_id=self.CURRENT_SCENE))

    def assert_nothing_left_this_server(self, session, action, console=""):
        """The four leavings a coordinate warp must not produce.

        `assertIsNone(action)` alone is what let round `741zlx`'s finding 10
        hide for a round: a shape can send no frame and still park a target,
        stage a login-scene entry or move the durable row, and every one of
        those reads downstream as "the warp happened".

        !! THE FIRST DRAFT OF THIS HELPER COULD NOT SEE TWO OF THE FOUR
        (pf-adversary, round `vlk8rq`, finding 2, MEASURED).  It read the
        parked target and the durable row off the session's EVENT list -- but
        `EVENT_WARP_TARGET_NOT_RECORDED` fires only when parking FAILS
        (`_park_warp_target`'s own docstring: "no event is emitted for
        success") and the persist prefix fires only on the no-coords branch.
        So a real parked target passed the "parks nothing" check.  Both are
        now read off the thing itself: the session attribute the parker
        writes, and a double standing in for the durable write door.
        """
        self.assertIsNone(action, "a closed coordinate warp composes no frame")
        self.assertFalse(
            self.login_scene_config_path.exists(),
            "a closed coordinate warp stages no login-scene entry",
        )
        # The attribute `_park_warp_target` actually writes, not an event that
        # only exists when it fails.  Same probe `test_gm_chat_command_action.
        # py::SameSceneForcePosClosedTests` uses for the closure below this
        # one.
        self.assertIsNone(
            getattr(session, "gm_last_warp_target", None),
            "a closed coordinate warp parks no destination",
        )
        self.assertEqual(
            [],
            [
                event
                for event in session.events
                if event.startswith(chat_command_action.EVENT_WARP_STAGED_PREFIX)
                or event.startswith(
                    chat_command_action.EVENT_WARP_SCENE_PERSIST_PREFIX
                )
            ],
            "a closed coordinate warp stages and persists nothing",
        )
        if console:
            # `2045` item 1 asks for THREE things and "a console line" is one
            # of them; asserting only the blocker table would leave the line
            # itself unpinned (pf-adversary, round `vlk8rq`, finding 7).
            self.assertIn(
                chat_command_action.OUTCOME_WARP_WITHHELD_TYPED_COORDS_CLOSED,
                console,
                "the refusal must reach the operator's console, not just the"
                " audit file",
            )

    def assert_named_the_closure(self, session):
        self.assertIn(
            chat_command_action.EVENT_WARP_WITHHELD_TYPED_COORDS_CLOSED,
            session.events,
            "the console/event trail must name WHICH closure held the command",
        )


class EveryTypedCoordinateShapeLeavesZeroBytesTests(_Case):
    """The three routes `_warp_action` can take a coordinate warp down."""

    def test_the_same_scene_force_pos_shape_sends_nothing(self):
        session = self.session_in_scene()
        action, console = self.act(session, f"/warp {self.CURRENT_SCENE} 100 200")
        self.assert_nothing_left_this_server(session, action, console)
        self.assert_named_the_closure(session)
        # NOT the neighbouring closure's word.  This shape was already shut
        # by `WARP_SAME_SCENE_FORCE_POS_AUTHORIZED`, one branch below; if the
        # trail says THAT, the new guard never ran and this file is green for
        # a second reason -- which is exactly the failure mode finding 10 was.
        self.assertNotIn(
            chat_command_action.EVENT_WARP_WITHHELD_FORCE_POS_CLOSED,
            session.events,
        )

    def test_the_cross_scene_live_teleport_shape_sends_nothing(self):
        """The shape finding 10 measured SENDING a real 73-byte frame."""
        session = self.session_in_scene()
        target = self.a_different_marker_backed_scene()
        self.assertTrue(
            warp_executor.WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED,
            "this test means the shape that is otherwise LIVE; if the live"
            " half is off, it is testing shape 3 twice",
        )
        action, console = self.act(session, f"/warp {target} 100 200")
        self.assert_nothing_left_this_server(session, action, console)
        self.assert_named_the_closure(session)

    def test_the_staging_fall_through_shape_stages_nothing(self):
        session = self.session_in_scene()
        target = self.a_different_marker_backed_scene()
        with mock.patch.object(
            warp_executor, "WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED", False
        ):
            action, console = self.act(session, f"/warp {target} 100 200")
        self.assert_nothing_left_this_server(session, action, console)
        self.assert_named_the_closure(session)


class TheGuardIsWhatDoesItTests(_Case):
    """This round's mutant, kept as a test instead of run by hand once.

    Delete the guard in `_warp_action` and the class above goes RED rather
    than passing for a second reason: the flip below shows the very same
    command composing a real frame the moment the flag says it may.
    """

    def test_flipping_the_flag_puts_the_cross_scene_frame_back(self):
        session = self.session_in_scene()
        target = self.a_different_marker_backed_scene()
        with mock.patch.object(
            warp_executor, "WARP_TYPED_COORDINATES_AUTHORIZED", True
        ):
            action, _console = self.act(session, f"/warp {target} 100 200")
        self.assertIsNotNone(
            action,
            "with the gate open this shape composes -- if it does not, the"
            " zero-byte results above prove nothing about the guard",
        )
        _label, _pc, frame, _delay = action
        self.assertGreater(len(frame), 0)
        self.assertNotIn(
            chat_command_action.EVENT_WARP_WITHHELD_TYPED_COORDS_CLOSED,
            session.events,
        )

    def test_the_guard_reads_the_flag_rather_than_a_copy_of_it(self):
        """No module-level snapshot: the patch above must really reach it."""
        session = self.session_in_scene()
        target = self.a_different_marker_backed_scene()
        with mock.patch.object(
            warp_executor, "WARP_TYPED_COORDINATES_AUTHORIZED", True
        ):
            first, _console = self.act(session, f"/warp {target} 100 200")
        second_session = self.session_in_scene()
        second, _console = self.act(second_session, f"/warp {target} 100 200")
        self.assertIsNotNone(first)
        self.assertIsNone(second)


class TheBareWarpIsUntouchedTests(_Case):
    """R306 passed `/warp <n>` five times, and Panya ruled it untouchable."""

    def test_a_bare_cross_scene_warp_still_composes(self):
        session = self.session_in_scene()
        target = self.a_different_marker_backed_scene()
        action, _console = self.act(session, f"/warp {target}")
        self.assertIsNotNone(
            action, "the closure is about TYPED COORDINATES, not about /warp"
        )
        self.assertNotIn(
            chat_command_action.EVENT_WARP_WITHHELD_TYPED_COORDS_CLOSED,
            session.events,
        )


class TheShippedGateTests(_Case):
    """The value and its citation, pinned the way both neighbours are."""

    def test_the_flag_ships_closed(self):
        self.assertIs(False, warp_executor.WARP_TYPED_COORDINATES_AUTHORIZED)

    def test_the_flag_carries_the_decision_that_closed_it(self):
        source = pathlib.Path(warp_executor.__file__).read_text(encoding="utf-8")
        block = source.split("WARP_TYPED_COORDINATES_AUTHORIZED")[0]
        self.assertIn("20260904_2045", block)
        self.assertIn("ErrorData=28317", block)

    def test_the_outcome_word_names_a_blocker_on_the_console(self):
        """A no-bytes outcome with no blocker sentence reads `no blocker
        recorded` to an attended tester -- the gap `ntf90h` D3 turned red."""
        self.assertIn(
            chat_command_action.OUTCOME_WARP_WITHHELD_TYPED_COORDS_CLOSED,
            chat_command_action.NO_BYTES_BLOCKERS,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
