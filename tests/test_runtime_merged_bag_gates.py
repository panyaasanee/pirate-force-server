"""The three runtime.py gates that used to compare against ONE merged bag.

CORE-REQUEST ``pf_bridge/notes_to_chief/20260908_0206_LANE-DB-CORE-REQUEST-*``
asked chief for a seam, not a rewrite: the three comparisons in ``runtime.py``
must ask ``inventory`` for the merged set at the moment they run, the way
``store.apply_v111_stack_merge`` already does, and the one that sits AFTER the
repository has committed must stop raising.

Two things are pinned here and nowhere else:

* the gates read the set THROUGH the module.  A ``from .inventory import``
  of a single value is what pf-adversary measured one layer down in
  ``store.py`` (D2 of that letter): the gate kept answering with the set that
  existed at import time.  Emptying ``STARTING_BACKPACKS`` at the moment of
  the call is the only fixture that can tell the two shapes apart.
* the committed-merge gate does not raise.  The row is already written when
  it runs, so an exception there escapes ``dispatch()`` with the DB changed
  and no bytes sent -- the failure LANE-DB measured on a five-bag set.

NOT claimed: that a five-bag set is safe.  Today the set holds one bag, so
every assertion below about a widened set is measured against a set this test
widens by hand, not against LANE-CS's real one (their ``#1091`` is not on
main).  See the round file for the open question about whether a SET is the
right shape for a post-condition at all.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import inventory  # noqa: E402
from pirateforce_foundation import runtime as runtime_module  # noqa: E402
from pirateforce_foundation.inventory import (  # noqa: E402
    INITIAL_BACKPACK,
    MERGED_V111_BACKPACK,
    V111_MERGE_REQUEST_PC,
)
from pirateforce_foundation.item_move_capture import (  # noqa: E402
    ITEM_MOVE_CAPTURE_REQUEST_PC,
    load_item_move_capture_scenario,
)
from pirateforce_foundation.item_move_hypothesis import (  # noqa: E402
    load_item_move_hypothesis_scenario,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector,
    load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
CAPTURE_SCENARIO = ROOT / "scenarios" / "item_move_capture_v111_slot2.json"
HYPOTHESIS_SCENARIO = ROOT / "scenarios" / "item_move_hypothesis_v111_slot2.json"


class MergedBagGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(Path(self.tmp.name) / "state.sqlite3",
                                 ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(1, 0, self.legacy.V135_PLAYER_X,
                     self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.capture_scenario = load_item_move_capture_scenario(CAPTURE_SCENARIO)
        self.hypothesis_scenario = load_item_move_hypothesis_scenario(
            HYPOTHESIS_SCENARIO
        )

    def _state(self, login, *, capture=False, hypothesis=False, create=True):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            item_move_capture_scenario=(
                self.capture_scenario if capture else None
            ),
            item_move_hypothesis_scenario=(
                self.hypothesis_scenario if hypothesis else None
            ),
        )
        state = state_type(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        if create:
            actions = state.dispatch(self.legacy.parse_outer(
                self.legacy._V25_REAL_CREATE_PC
            ))
            self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        characters = self.store.list_characters(state.foundation.account_id)
        self.assertEqual(len(characters), 1)
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = True
        return state, characters[0]

    def _merged_state(self, login, **kind):
        """A character that has already merged, reconnected under ``kind``."""
        baseline, character = self._state(login)
        actions = baseline.dispatch(self.legacy.parse_outer(V111_MERGE_REQUEST_PC))
        self.assertEqual(len(actions), 1)
        self.assertEqual(baseline.foundation.backpack, MERGED_V111_BACKPACK)
        baseline.foundation.close_connection()
        state, same = self._state(login, create=False, **kind)
        self.assertEqual(same.id, character.id)
        self.assertEqual(state.foundation.backpack, MERGED_V111_BACKPACK)
        return state, same

    def _rows(self, character_id):
        with self.store.connect() as db:
            return db.execute(
                "SELECT item_identity,template_id,quantity,slot "
                "FROM character_backpack_items WHERE character_id=? "
                "ORDER BY item_identity",
                (character_id,),
            ).fetchall()

    def _empty_the_set_after(self, session):
        """Empty the merged set the instant the repository call returns.

        The post-commit gate cannot be reached with a globally empty set --
        ``store.apply_v111_stack_merge`` reads the same set and would refuse
        the write first, which is the ordering that makes the whole request
        safe.  Flipping between the two is the only way to stand where the
        gate stands: row written, set no longer holding the state.
        """
        real = inventory.merged_v111_states
        flipped = {"on": False}
        original_merge = session.merge_v111_stack

        def merge():
            applied = original_merge()
            flipped["on"] = True
            return applied

        session.merge_v111_stack = merge
        return mock.patch.object(
            inventory, "merged_v111_states",
            lambda: () if flipped["on"] else real(),
        )

    # ------------------------------------------------------------------
    # the committed-merge gate

    def test_the_committed_merge_gate_does_not_raise_after_the_write(self):
        state, character = self._state("committed")
        with self._empty_the_set_after(state.foundation):
            actions = state.dispatch(
                self.legacy.parse_outer(V111_MERGE_REQUEST_PC)
            )
        self.assertEqual(actions, [])
        self.assertIn(
            "foundation_v111_merge_committed_unknown_state_no_reply",
            state.events,
        )
        self.assertEqual(state.stack_merge_count, 0)

    def test_the_row_really_was_written_before_that_gate_ran(self):
        """The control the whole request exists for.

        If this row were absent the gate would be a precondition and raising
        would have cost nothing.  It is present: the exception the old code
        raised travelled out of ``dispatch()`` with the DB already changed.
        """
        state, character = self._state("committed-row")
        before = self._rows(character.id)
        with self._empty_the_set_after(state.foundation):
            state.dispatch(self.legacy.parse_outer(V111_MERGE_REQUEST_PC))
        after = self._rows(character.id)
        self.assertNotEqual(before, after)
        self.assertNotIn(3, [row[0] for row in after])

    def test_the_committed_merge_gate_still_replies_on_the_real_set(self):
        state, character = self._state("committed-ok")
        actions = state.dispatch(self.legacy.parse_outer(V111_MERGE_REQUEST_PC))
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            actions[0][0],
            "FOUNDATION_V111_ITEM_STACK_ID3_INTO_ID1_QTY2_COMMITTED",
        )
        self.assertEqual(state.stack_merge_count, 1)
        self.assertNotIn(
            "foundation_v111_merge_committed_unknown_state_no_reply",
            state.events,
        )

    # ------------------------------------------------------------------
    # the two preconditions read the set live

    def test_the_capture_gate_reads_the_set_through_the_module(self):
        state, _ = self._merged_state("capture", capture=True)
        with mock.patch.object(inventory, "STARTING_BACKPACKS", ()):
            self.assertEqual(inventory.merged_v111_states(), ())
            actions = state.dispatch(
                self.legacy.parse_outer(ITEM_MOVE_CAPTURE_REQUEST_PC)
            )
        self.assertEqual(actions, [])
        self.assertIn(
            "item_move_capture_wrong_current_state_no_reply", state.events
        )
        self.assertEqual(state.item_move_capture_count, 0)

    def test_the_capture_gate_admits_the_bag_on_the_real_set(self):
        state, _ = self._merged_state("capture-ok", capture=True)
        actions = state.dispatch(
            self.legacy.parse_outer(ITEM_MOVE_CAPTURE_REQUEST_PC)
        )
        self.assertEqual(actions, [])
        self.assertIn(
            "item_move_capture_exact_op4_slot2_id1_no_reply", state.events
        )
        self.assertEqual(state.item_move_capture_count, 1)

    def test_the_hypothesis_gate_reads_the_set_through_the_module(self):
        state, _ = self._merged_state("hypothesis", hypothesis=True)
        with mock.patch.object(inventory, "STARTING_BACKPACKS", ()):
            actions = state.dispatch(self.legacy.parse_outer(
                ITEM_MOVE_CAPTURE_REQUEST_PC
            ))
        self.assertEqual(actions, [])
        self.assertIn(
            "item_move_hypothesis_wrong_current_state_no_reply", state.events
        )

    # ------------------------------------------------------------------
    # the set is the thing that grows, and runtime holds no copy of it

    def test_a_widened_set_carries_the_second_bags_merged_state(self):
        # The class weapon row (identity 4) is the one LANE-CS varies per
        # class, and it is the row the V111 merge never touches -- so a
        # second bag built this way still merges, which is the whole point:
        # its merged counterpart differs from MERGED_V111_BACKPACK in
        # exactly that row.
        second = replace(
            INITIAL_BACKPACK,
            items=tuple(
                replace(item, template_id=item.template_id + 1)
                if item.identity == 4 else item
                for item in INITIAL_BACKPACK.items
            ),
        )
        self.assertTrue(inventory.can_merge_v111(second))
        self.assertNotEqual(second, INITIAL_BACKPACK)
        with mock.patch.object(
            inventory, "STARTING_BACKPACKS", (INITIAL_BACKPACK, second)
        ):
            states = inventory.merged_v111_states()
            self.assertEqual(len(states), 2)
            self.assertIn(MERGED_V111_BACKPACK, states)
            self.assertIn(inventory.merged_v111_state(second), states)
            self.assertNotEqual(
                inventory.merged_v111_state(second), MERGED_V111_BACKPACK
            )

    def test_runtime_binds_no_copy_of_the_single_merged_bag(self):
        """The D2 shape, pinned one layer up.

        ``store.py`` held ``from .inventory import MERGED_V111_BACKPACK`` and
        its third gate never moved with the set.  If anyone re-imports the
        name into ``runtime`` this goes red before the behaviour drifts.
        """
        self.assertNotIn("MERGED_V111_BACKPACK", vars(runtime_module))
        source = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("MERGED_V111_BACKPACK", source)
        self.assertIn("from . import inventory", source)
        self.assertEqual(source.count("inventory.merged_v111_states()"), 3)


if __name__ == "__main__":
    unittest.main()
