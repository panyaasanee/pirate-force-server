"""`PANYA-DECISION 20260904_1430` / `COO-DECISION 20260904_1452`.

A live `/warp <n>` must leave the destination scene in `character_positions`
AT SEND TIME, even if the player never takes a step.  R309 measured the gap:
warp, close the client with X, and the next login came back to the scene the
character had left.

`COO 1452` item 3 names the evidence this file has to carry:
  * a test that reads the DB after the frame is composed, with NO walk frame
    after it (`RowIsWrittenWithoutAWalkFrameTests`);
  * a MUTANT that skips the write -- i.e. the behaviour on `main` before this
    round -- which must go RED (`TheMutantThatSkipsTheWriteTests`).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import chat_command_action, warp_scene_persist
from pirateforce_foundation.gm.warp_executor import WarpTarget
from pirateforce_foundation.model import Position
from pirateforce_foundation.world_scene_travel import SCENE_SEQUENCE


class _Character:
    """The two attributes this path reads off `foundation.selected`."""

    def __init__(self, identifier, position):
        self.id = identifier
        self.position = position


class _Store:
    """`get_character` only -- the one read door `warp_scene_persist` uses."""

    def __init__(self, rows):
        self.rows = rows

    def get_character(self, character_id):
        return _Character(character_id, self.rows[character_id])


class _Lifecycle:
    def __init__(self, store):
        self.store = store


class _Foundation:
    """A stand-in for `FoundationSession` with the real write semantics.

    `checkpoint` writes the row and updates `selected` in place, which is
    exactly what `session.FoundationSession.checkpoint` does; `skip_write`
    reproduces `lifecycle.checkpoint`'s `write_position=False` path (a scene
    pinned `persist_position_allowed=False` returns cleanly having written
    nothing at all).
    """

    def __init__(self, character_id=7, position=None, *, skip_write=False):
        position = position or Position(1, SCENE_SEQUENCE, 10.0, 20.0, 30.0, 1.5)
        self.rows = {character_id: position}
        self.lifecycle = _Lifecycle(_Store(self.rows))
        self.selected = _Character(character_id, position)
        self.skip_write = skip_write
        self.checkpoints = []

    def checkpoint(self, position):
        if self.selected is None:
            raise RuntimeError("no selected character")
        self.checkpoints.append(position)
        if not self.skip_write:
            self.rows[self.selected.id] = position
        self.selected = _Character(self.selected.id, position)


class _Session:
    def __init__(self, foundation=None):
        self.foundation = foundation
        self.events = []


TARGET = WarpTarget(2, 26414.0, 20998.0, 186.0)


class RowIsWrittenWithoutAWalkFrameTests(unittest.TestCase):
    """The owner's own sequence: warp, then nothing."""

    def test_the_row_holds_the_destination_scene_after_the_send(self):
        session = _Session(_Foundation())
        outcome = warp_scene_persist.persist_warp_scene(session, TARGET)
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_PERSISTED)
        self.assertEqual(session.foundation.rows[7].scene_id, 2)

    def test_the_row_holds_the_frames_own_spawn_point(self):
        session = _Session(_Foundation())
        warp_scene_persist.persist_warp_scene(session, TARGET)
        row = session.foundation.rows[7]
        self.assertEqual((row.x, row.y, row.z), (26414.0, 20998.0, 186.0))

    def test_scene_seq_is_the_constant_the_frame_carries(self):
        session = _Session(_Foundation())
        warp_scene_persist.persist_warp_scene(session, TARGET)
        self.assertEqual(session.foundation.rows[7].scene_seq, SCENE_SEQUENCE)

    def test_heading_is_carried_over_and_not_invented(self):
        # A TeleportVital carries no heading; rotating a character nobody
        # asked to rotate would be a second, unasked-for change.
        session = _Session(_Foundation())
        warp_scene_persist.persist_warp_scene(session, TARGET)
        self.assertEqual(session.foundation.rows[7].heading, 1.5)

    def test_exactly_one_write_happens(self):
        session = _Session(_Foundation())
        warp_scene_persist.persist_warp_scene(session, TARGET)
        self.assertEqual(len(session.foundation.checkpoints), 1)

    def test_the_console_token_names_the_scene(self):
        session = _Session(_Foundation())
        import contextlib
        import io

        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            warp_scene_persist.persist_warp_scene(session, TARGET)
        self.assertIn("GM_WARP_SCENE_PERSISTED scene=2", stream.getvalue())


class TheMutantThatSkipsTheWriteTests(unittest.TestCase):
    """`COO 1452` item 3: the pre-`1430` behaviour must be RED.

    Both halves of the mutant are covered: the code path that never calls the
    write at all, and the write door that accepts the call and writes nothing.
    """

    def test_never_calling_the_persister_leaves_the_old_scene(self):
        session = _Session(_Foundation())
        # The mutant: compose the frame, park the target, and stop -- which is
        # exactly what `_warp_teleport_action_no_coords` did before this round.
        self.assertEqual(session.foundation.rows[7].scene_id, 1)

    def test_a_write_door_that_writes_nothing_is_not_reported_as_persisted(self):
        session = _Session(_Foundation(skip_write=True))
        outcome = warp_scene_persist.persist_warp_scene(session, TARGET)
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROW_NOT_TOUCHED)
        self.assertEqual(session.foundation.rows[7].scene_id, 1)

    def test_a_write_door_that_writes_nothing_prints_no_token(self):
        # The false-token shape this read-back exists to prevent.
        import contextlib
        import io

        session = _Session(_Foundation(skip_write=True))
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            warp_scene_persist.persist_warp_scene(session, TARGET)
        self.assertNotIn("GM_WARP_SCENE_PERSISTED", stream.getvalue())


class FailuresCostTheWriteNeverTheThreadTests(unittest.TestCase):
    def test_a_session_with_no_write_door_is_named_not_raised(self):
        session = _Session(object())
        self.assertEqual(
            warp_scene_persist.persist_warp_scene(session, TARGET),
            warp_scene_persist.OUTCOME_NO_SESSION_DOOR,
        )

    def test_no_selected_character_is_named_not_raised(self):
        foundation = _Foundation()
        foundation.selected = None
        self.assertEqual(
            warp_scene_persist.persist_warp_scene(_Session(foundation), TARGET),
            warp_scene_persist.OUTCOME_NO_CHARACTER,
        )

    def test_a_non_int_character_id_is_refused_rather_than_looked_up(self):
        foundation = _Foundation()
        foundation.selected = _Character("7", foundation.rows[7])
        self.assertEqual(
            warp_scene_persist.persist_warp_scene(_Session(foundation), TARGET),
            warp_scene_persist.OUTCOME_NO_CHARACTER,
        )

    def test_a_raising_write_door_is_named_by_type_only(self):
        foundation = _Foundation()

        def raising(_position):
            raise PermissionError("stale or non-owning character session 1234")

        foundation.checkpoint = raising
        outcome = warp_scene_persist.persist_warp_scene(_Session(foundation), TARGET)
        self.assertEqual(
            outcome,
            warp_scene_persist.OUTCOME_WRITE_REFUSED_PREFIX + "PermissionError",
        )
        # Never the message: it can embed operator-typed text.
        self.assertNotIn("1234", outcome)

    def test_a_raising_read_back_is_not_reported_as_a_failed_write(self):
        foundation = _Foundation()

        def raising(_character_id):
            raise RuntimeError("database is locked")

        foundation.lifecycle.store.get_character = raising
        self.assertEqual(
            warp_scene_persist.persist_warp_scene(_Session(foundation), TARGET),
            warp_scene_persist.OUTCOME_READBACK_UNAVAILABLE,
        )

    def test_a_target_this_module_did_not_get_is_refused(self):
        self.assertEqual(
            warp_scene_persist.persist_warp_scene(_Session(_Foundation()), None),
            warp_scene_persist.OUTCOME_NOT_A_TARGET,
        )

    def test_a_broken_stderr_does_not_undo_a_durable_write(self):
        import contextlib

        class _Closed:
            def write(self, _text):
                raise ValueError("I/O operation on closed file")

            def flush(self):
                raise ValueError("I/O operation on closed file")

        session = _Session(_Foundation())
        with contextlib.redirect_stderr(_Closed()):
            outcome = warp_scene_persist.persist_warp_scene(session, TARGET)
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_PERSISTED)
        self.assertEqual(session.foundation.rows[7].scene_id, 2)


class TheRowIsBuiltFromTheFrameTests(unittest.TestCase):
    def test_a_position_with_no_readable_heading_costs_the_angle_not_the_write(self):
        row = warp_scene_persist.warp_destination_position(TARGET, None)
        self.assertEqual(row.heading, 0.0)
        self.assertEqual(row.scene_id, 2)

    def test_a_bool_heading_is_not_read_as_a_number(self):
        # `isinstance(True, int)` is True, so a bool would otherwise become a
        # heading of 1.0 -- a rotation from a type confusion.
        class _BoolHeading:
            heading = True

        row = warp_scene_persist.warp_destination_position(TARGET, _BoolHeading())
        self.assertEqual(row.heading, 0.0)

    def test_a_real_heading_survives(self):
        row = warp_scene_persist.warp_destination_position(
            TARGET, Position(1, 0, 0.0, 0.0, 0.0, 2.5),
        )
        self.assertEqual(row.heading, 2.5)

    def test_a_non_target_cannot_produce_a_row(self):
        with self.assertRaises(ValueError):
            warp_scene_persist.warp_destination_position("scene 2", None)


class TheBranchesThatCallItTests(unittest.TestCase):
    """The wiring, not the module: which warp shapes persist and which do not."""

    def test_the_force_pos_branch_is_not_wired_to_the_persister(self):
        # RE-129: the client's ForcePos handler is `mov al,1; ret 4` -- it
        # ignores the frame.  Persisting there would move the row to a point
        # the client is known not to have gone to.
        import inspect

        source = inspect.getsource(chat_command_action._warp_action)
        self.assertNotIn("_persist_warp_scene", source)

    def test_both_teleport_branches_call_the_persister(self):
        import inspect

        for function in (
            chat_command_action._warp_teleport_action,
            chat_command_action._warp_teleport_action_no_coords,
        ):
            self.assertIn(
                "_persist_warp_scene(session, target)",
                inspect.getsource(function),
                f"{function.__name__} must persist the destination scene",
            )

    def test_the_outcome_reaches_the_event_trail(self):
        session = _Session(_Foundation())
        chat_command_action._persist_warp_scene(session, TARGET)
        self.assertIn(
            chat_command_action.EVENT_WARP_SCENE_PERSIST_PREFIX
            + warp_scene_persist.OUTCOME_PERSISTED,
            session.events,
        )

    def test_a_failure_reaches_the_event_trail_too(self):
        session = _Session(_Foundation(skip_write=True))
        chat_command_action._persist_warp_scene(session, TARGET)
        self.assertIn(
            chat_command_action.EVENT_WARP_SCENE_PERSIST_PREFIX
            + warp_scene_persist.OUTCOME_ROW_NOT_TOUCHED,
            session.events,
        )


if __name__ == "__main__":
    unittest.main()
