import hashlib
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.inventory import (
    INITIAL_BACKPACK,
    MERGED_V111_BACKPACK,
    V111_MERGE_REQUEST_PC,
    make_backpack_attr,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.session import FoundationSession, ReadOnlyFoundationSession
from pirateforce_foundation.store import SQLiteStore


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


class ItemLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.default = Position(
            1, 0, self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, self.default,
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def preset(self, name="test01"):
        actor = self.legacy.get_preset_actor_wire()
        old = self.legacy.wstr_tag("test01")
        if name == "test01":
            return actor
        self.assertEqual(actor.count(old), 1)
        return actor.replace(old, self.legacy.wstr_tag(name), 1)

    def ready_state(self, login="item", *, create=True):
        state = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        if create:
            created = state.dispatch(self.legacy.parse_outer(
                self.legacy._V25_REAL_CREATE_PC
            ))
            self.assertEqual(created[0][0], "FOUNDATION_CREATE_COMMITTED")
        characters = self.store.list_characters(state.foundation.account_id)
        self.assertEqual(len(characters), 1)
        entered = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        self.assertEqual(entered[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = True
        return state, characters[0], entered[0][1], entered[0][2]

    def exact_merge(self):
        return self.legacy.parse_outer(V111_MERGE_REQUEST_PC)

    def move_identity_one_to_slot_three(self):
        pc = (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.ITEM_OPERATE_REQ_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.u8tag(0x0B, 4)
            + self.legacy.u32tag(0x14, 3)
            + self.legacy.qwordtag(0x32, 1)
        )
        return self.legacy.parse_outer(pc)

    def test_initial_seed_projection_and_golden_are_byte_exact(self):
        state, character, start_pc, start_frame = self.ready_state("golden")
        self.assertEqual(state.foundation.backpack, INITIAL_BACKPACK)
        initial_wire = make_backpack_attr(self.legacy, INITIAL_BACKPACK)
        self.assertEqual(initial_wire, self.legacy.make_backpack_attr_four_items())
        self.assertEqual(start_pc.count(initial_wire), 1)

        golden = json.loads(
            (ROOT / "tests/golden/item_lifecycle_v1.json").read_text(
                encoding="utf-8"
            )
        )
        actual = {
            "initial_backpack_sha256": hashlib.sha256(initial_wire).hexdigest().upper(),
            "initial_start_pc_sha256": hashlib.sha256(start_pc).hexdigest().upper(),
            "initial_start_frame_sha256": hashlib.sha256(start_frame).hexdigest().upper(),
        }
        self.assertEqual(actual, {key: golden[key] for key in actual})
        self.assertEqual(
            self.store.get_backpack(state.foundation.session_id, character.id),
            INITIAL_BACKPACK,
        )

    def test_exact_merge_commits_before_reply_and_survives_reconnect(self):
        state, character, _, _ = self.ready_state("persist")
        order = []
        original_builder = self.legacy.make_item_operate_stack_merge_success
        original_apply = self.store.apply_v111_stack_merge

        def build_response():
            order.append("response_built")
            return original_builder()

        def apply(sid, character_id):
            self.assertEqual(state.foundation.backpack, INITIAL_BACKPACK)
            order.append("transaction")
            result = original_apply(sid, character_id)
            self.assertEqual(result, MERGED_V111_BACKPACK)
            # Store commit completed while connection-local memory is still pre-state.
            self.assertEqual(state.foundation.backpack, INITIAL_BACKPACK)
            return result

        with mock.patch.object(
            self.legacy, "make_item_operate_stack_merge_success",
            side_effect=build_response,
        ), mock.patch.object(
            self.store, "apply_v111_stack_merge", side_effect=apply,
        ):
            actions = state.dispatch(self.exact_merge())

        expected_pc, expected_frame = original_builder()
        self.assertEqual(order, ["response_built", "transaction"])
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0][1:], (expected_pc, expected_frame, 0.0))
        self.assertEqual(state.foundation.backpack, MERGED_V111_BACKPACK)
        self.assertEqual(state.item_quantity, 2)
        self.assertFalse(state.stack_source_present)
        self.assertEqual(
            self.store.get_backpack(state.foundation.session_id, character.id),
            MERGED_V111_BACKPACK,
        )

        reopened, same, start_pc, start_frame = self.ready_state(
            "persist", create=False
        )
        self.assertEqual(same.id, character.id)
        self.assertEqual(reopened.foundation.backpack, MERGED_V111_BACKPACK)
        merged_wire = make_backpack_attr(self.legacy, MERGED_V111_BACKPACK)
        self.assertEqual(start_pc.count(merged_wire), 1)
        self.assertNotIn(self.legacy.qwordtag(0x32, 3), merged_wire)
        self.assertEqual(reopened.dispatch(self.exact_merge()), [])
        self.assertIn("foundation_v111_merge_replay_no_reply", reopened.events)

        golden = json.loads(
            (ROOT / "tests/golden/item_lifecycle_v1.json").read_text(
                encoding="utf-8"
            )
        )
        actual = {
            "merged_backpack_sha256": hashlib.sha256(merged_wire).hexdigest().upper(),
            "merge_response_pc_sha256": hashlib.sha256(expected_pc).hexdigest().upper(),
            "merge_response_frame_sha256": hashlib.sha256(expected_frame).hexdigest().upper(),
            "merged_start_pc_sha256": hashlib.sha256(start_pc).hexdigest().upper(),
            "merged_start_frame_sha256": hashlib.sha256(start_frame).hexdigest().upper(),
        }
        self.assertEqual(actual, {key: golden[key] for key in actual})

    def test_wrong_envelope_and_trailing_candidate_fail_closed(self):
        state, character, _, _ = self.ready_state("malformed")
        variants = []
        for attribute, value in (
            ("outer_id", self.legacy.GSCN_RUNTIME_PROTOCOL_REQ + 1),
            ("outer_version", 1),
            ("outer_mask", 3),
            ("vital_count", 2),
            ("nested_version", 1),
        ):
            parsed = self.exact_merge()
            setattr(parsed, attribute, value)
            variants.append(parsed)
        variants.append(self.legacy.parse_outer(V111_MERGE_REQUEST_PC + b"\x00"))

        for parsed in variants:
            self.assertEqual(state.dispatch(parsed), [])
        self.assertEqual(state.stack_merge_count, 0)
        self.assertEqual(state.foundation.backpack, INITIAL_BACKPACK)
        self.assertEqual(
            self.store.get_backpack(state.foundation.session_id, character.id),
            INITIAL_BACKPACK,
        )
        self.assertEqual(
            state.events.count(
                "foundation_v111_merge_candidate_wrong_envelope_no_reply"
            ),
            len(variants),
        )

    def test_wrong_sequence_builder_and_repository_failures_do_not_mutate(self):
        state, character, _, _ = self.ready_state("failure")
        state.runtime_ack_sent = False
        self.assertEqual(state.dispatch(self.exact_merge()), [])
        state.runtime_ack_sent = True

        with mock.patch.object(
            self.legacy, "make_item_operate_stack_merge_success",
            side_effect=RuntimeError("builder failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "builder failed"):
                state.dispatch(self.exact_merge())
        self.assertEqual(state.foundation.backpack, INITIAL_BACKPACK)

        with mock.patch.object(
            self.store, "apply_v111_stack_merge",
            side_effect=sqlite3.OperationalError("injected rollback"),
        ):
            self.assertEqual(state.dispatch(self.exact_merge()), [])
        self.assertEqual(state.foundation.backpack, INITIAL_BACKPACK)
        self.assertEqual(state.item_quantity, 1)
        self.assertTrue(state.stack_source_present)
        self.assertEqual(
            self.store.get_backpack(state.foundation.session_id, character.id),
            INITIAL_BACKPACK,
        )

    def test_transaction_rollback_and_create_seed_are_atomic(self):
        state, character, _, _ = self.ready_state("rollback")
        with self.store.connect() as db:
            db.execute(
                "CREATE TRIGGER reject_v111 BEFORE DELETE ON character_backpack_items "
                "BEGIN SELECT RAISE(ABORT,'reject merge'); END"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.apply_v111_stack_merge(
                state.foundation.session_id, character.id
            )
        self.assertEqual(
            self.store.get_backpack(state.foundation.session_id, character.id),
            INITIAL_BACKPACK,
        )

        other_db = Path(self.tmp.name) / "create-atomic.sqlite3"
        other_store = SQLiteStore(other_db, ROOT / "migrations")
        other_store.migrate()
        with other_store.connect() as db:
            db.execute(
                "CREATE TRIGGER reject_seed BEFORE INSERT ON character_backpacks "
                "BEGIN SELECT RAISE(ABORT,'reject seed'); END"
            )
        other_lifecycle = CharacterLifecycle(
            other_store, self.default,
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        create_state = make_state_class(
            self.legacy, other_lifecycle, self.projector,
        )("create-atomic")
        create_state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        self.assertEqual(create_state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        )), [])
        self.assertEqual(
            other_store.list_characters(create_state.foundation.account_id), []
        )
        with other_store.connect() as db:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM character_positions").fetchone()[0],
                0,
            )
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM character_backpacks").fetchone()[0],
                0,
            )

    def test_session_account_and_concurrent_replay_isolation(self):
        first, character, _, _ = self.ready_state("owner")
        second, same, _, _ = self.ready_state("owner", create=False)
        self.assertEqual(same.id, character.id)
        with self.assertRaises(PermissionError):
            self.store.apply_v111_stack_merge(
                first.foundation.session_id, character.id
            )

        foreign, foreign_character, _, _ = self.ready_state("foreign")
        with self.assertRaises(PermissionError):
            self.store.apply_v111_stack_merge(
                foreign.foundation.session_id, character.id
            )
        self.assertEqual(
            self.store.get_backpack(
                foreign.foundation.session_id, foreign_character.id
            ),
            INITIAL_BACKPACK,
        )

        barrier = threading.Barrier(3)
        results = []
        errors = []

        def worker():
            barrier.wait()
            try:
                results.append(self.store.apply_v111_stack_merge(
                    second.foundation.session_id, character.id
                ))
            except Exception as error:  # pragma: no cover - asserted below
                errors.append(error)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(results.count(MERGED_V111_BACKPACK), 1)
        self.assertEqual(results.count(None), 1)

    def test_unrelated_move_falls_through_without_persistence(self):
        state, character, _, _ = self.ready_state("fallback")
        actions = state.dispatch(self.move_identity_one_to_slot_three())
        self.assertIn(
            "V111_ITEM_MOVE_ID1_SLOT0_TO_SLOT3_SUCCESS",
            [action[0] for action in actions],
        )
        self.assertEqual(state.item_slot, 3)
        self.assertEqual(
            self.store.get_backpack(state.foundation.session_id, character.id),
            INITIAL_BACKPACK,
        )

    def test_unknown_persisted_shape_and_read_only_mutation_reject(self):
        state, character, _, _ = self.ready_state("strict")
        with self.store.connect() as db:
            db.execute(
                "UPDATE character_backpack_items SET quantity=2 "
                "WHERE character_id=? AND item_identity=2",
                (character.id,),
            )
        with self.assertRaisesRegex(ValueError, "outside the governed V111 allowlist"):
            self.store.get_backpack(state.foundation.session_id, character.id)
        with self.assertRaisesRegex(ValueError, "outside the governed V111 allowlist"):
            self.store.apply_v111_stack_merge(
                state.foundation.session_id, character.id
            )
        with self.assertRaises(PermissionError):
            ReadOnlyFoundationSession.merge_v111_stack(object())


if __name__ == "__main__":
    unittest.main()
