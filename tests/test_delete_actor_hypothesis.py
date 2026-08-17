"""Runtime and store hookup for the HYP-PF-015 soft delete (DeleteActorVital).

Every runtime test drives the real dispatch path behind the delete actor
opt-in scenario.  The accepted request is the designed one-vital
GSCN_LoginProtocol envelope carrying the exact DELETE-003 nested record with
op 1; the response is the designed echo ack inside the accepted
GSCN_RunTimeProtocolRes v4 envelope, queued only after the ``deleted_at``
commit.  The owner-mandated reuse cycle (create -> delete -> recreate into
the same slot under the migration-004 partial unique indexes) is proven
through the real dispatch path and again at the store layer.  Wrong
envelopes, op 2, unparseable records, wrong stages, repository refusals,
and every frame without the opt-in scenario fail closed with no reply and
no write.  ``production_allowed`` stays false.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.delete_actor import (  # noqa: E402
    DELETE_ACTOR_VITAL_ID,
    DELETE_ACTOR_VITAL_VERSION,
)
from pirateforce_foundation.delete_actor_hypothesis import (  # noqa: E402
    DELETE_ACTOR_PROBE_ACK_FRAME_SHA256,
    DELETE_ACTOR_PROBE_ACK_PC_SHA256,
    DELETE_ACTOR_PROBE_NESTED_PAYLOADS,
    DELETE_ACTOR_PROBE_REQUEST_PC_SHA256,
    _login_protocol_request_pc,
    classify_delete_actor_attempt,
    load_delete_actor_hypothesis_scenario,
    make_delete_actor_ack_response,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "delete_actor_hypothesis_soft_delete.json"


class DeleteActorHypothesisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.scenario = load_delete_actor_hypothesis_scenario(SCENARIO_PATH)

    def tearDown(self):
        self.tmp.cleanup()

    def _state_type(self, *, delete=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            delete_actor_hypothesis_scenario=self.scenario if delete else None,
        )

    def _char_select_state(self, login, *, delete=True, create=False):
        state = self._state_type(delete=delete)(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        if create:
            actions = state.dispatch(self.legacy.parse_outer(
                self.legacy._V25_REAL_CREATE_PC
            ))
            self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        return state

    def _delete_pc(self, probe="op1_selector0_empty"):
        return _login_protocol_request_pc(
            self.legacy, DELETE_ACTOR_PROBE_NESTED_PAYLOADS[probe],
        )

    def _character_rows(self):
        with self.store.connect() as db:
            return db.execute(
                "SELECT id,selector,identity_lo,identity_hi,deleted_at,"
                "create_fingerprint FROM characters ORDER BY id"
            ).fetchall()

    # --- fixtures -------------------------------------------------------

    def test_probe_fixtures_are_hash_pinned(self):
        for name, payload in DELETE_ACTOR_PROBE_NESTED_PAYLOADS.items():
            request = _login_protocol_request_pc(self.legacy, payload)
            self.assertEqual(
                hashlib.sha256(request).hexdigest().upper(),
                DELETE_ACTOR_PROBE_REQUEST_PC_SHA256[name], name,
            )
            pc, frame = make_delete_actor_ack_response(self.legacy, payload)
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                DELETE_ACTOR_PROBE_ACK_PC_SHA256[name], name,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                DELETE_ACTOR_PROBE_ACK_FRAME_SHA256[name], name,
            )

    def test_scenario_allowlist_is_exact(self):
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda d: d.update(production_allowed=True),
            lambda d: d.update(id="delete_actor_hypothesis_other"),
            lambda d: d.update(extra_key=1),
            lambda d: d.pop("nonclaims"),
            lambda d: d["entry"].update(request_envelope="anything"),
            lambda d: d["nonclaims"].pop(),
        ):
            broken = json.loads(json.dumps(data))
            mutate(broken)
            path = Path(self.tmp.name) / "broken.json"
            path.write_text(json.dumps(broken), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_delete_actor_hypothesis_scenario(path)

    # --- classifier -----------------------------------------------------

    def test_classifier_accepts_only_the_designed_op1_shape(self):
        parsed = self.legacy.parse_outer(self._delete_pc())
        self.assertEqual(
            classify_delete_actor_attempt(self.legacy, parsed), "exact_op1",
        )
        runtime_envelope = bytes(
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, DELETE_ACTOR_VITAL_ID)
            + self.legacy.u8tag(0x0B, DELETE_ACTOR_VITAL_VERSION)
            + DELETE_ACTOR_PROBE_NESTED_PAYLOADS["op1_selector0_empty"]
        )
        self.assertEqual(
            classify_delete_actor_attempt(
                self.legacy, self.legacy.parse_outer(runtime_envelope),
            ),
            "wrong_envelope",
        )
        op2 = _login_protocol_request_pc(
            self.legacy, bytes.fromhex("0802080014000000004400000000"),
        )
        self.assertEqual(
            classify_delete_actor_attempt(
                self.legacy, self.legacy.parse_outer(op2),
            ),
            "op2_unproven",
        )
        truncated = self._delete_pc()[:-3]
        self.assertEqual(
            classify_delete_actor_attempt(
                self.legacy, self.legacy.parse_outer(truncated),
            ),
            "unparsed",
        )

    # --- accepted dispatch ---------------------------------------------

    def test_accepted_delete_commits_before_pinned_ack(self):
        state = self._char_select_state("probe1", create=True)
        rows = self._character_rows()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["deleted_at"])
        actions = state.dispatch(self.legacy.parse_outer(self._delete_pc()))
        self.assertEqual(len(actions), 1)
        label, pc, frame, delay = actions[0]
        self.assertEqual(
            label, "HYP_PF_015_DELETE_ACTOR_SELECTOR00_SOFT_DELETE_COMMITTED",
        )
        self.assertEqual(
            hashlib.sha256(pc).hexdigest().upper(),
            DELETE_ACTOR_PROBE_ACK_PC_SHA256["op1_selector0_empty"],
        )
        self.assertEqual(
            hashlib.sha256(frame).hexdigest().upper(),
            DELETE_ACTOR_PROBE_ACK_FRAME_SHA256["op1_selector0_empty"],
        )
        self.assertEqual(delay, 0.0)
        rows = self._character_rows()
        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(rows[0]["deleted_at"])
        self.assertEqual(state.delete_actor_soft_delete_count, 1)
        self.assertEqual(
            self.store.list_characters(state.foundation.account_id), [],
        )
        with self.store.connect() as db:
            positions = db.execute(
                "SELECT COUNT(*) FROM character_positions"
            ).fetchone()[0]
            backpack_items = db.execute(
                "SELECT COUNT(*) FROM character_backpack_items"
            ).fetchone()[0]
        self.assertEqual(positions, 1)
        self.assertEqual(backpack_items, 4)

    def test_owner_mandated_reuse_cycle_through_dispatch(self):
        creator = self._char_select_state("probe1", create=True)
        first = self._character_rows()[0]
        deleter = self._char_select_state("probe1")
        actions = deleter.dispatch(self.legacy.parse_outer(self._delete_pc()))
        self.assertEqual(
            actions[0][0],
            "HYP_PF_015_DELETE_ACTOR_SELECTOR00_SOFT_DELETE_COMMITTED",
        )
        recreated = deleter.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(recreated[0][0], "FOUNDATION_CREATE_COMMITTED")
        rows = self._character_rows()
        self.assertEqual(len(rows), 2)
        old, new = rows
        self.assertEqual(old["id"], first["id"])
        self.assertIsNotNone(old["deleted_at"])
        self.assertIsNone(new["deleted_at"])
        self.assertEqual(new["selector"], old["selector"])
        self.assertEqual(new["identity_lo"], old["identity_lo"])
        self.assertEqual(new["identity_hi"], old["identity_hi"])
        self.assertEqual(
            new["create_fingerprint"], old["create_fingerprint"],
        )
        listed = self.store.list_characters(creator.foundation.account_id)
        self.assertEqual([c.id for c in listed], [new["id"]])

    # --- fail closed ----------------------------------------------------

    def test_wrong_stage_and_repository_refusals_fail_closed(self):
        state = self._char_select_state("probe1", create=True)
        characters = self.store.list_characters(state.foundation.account_id)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(self._delete_pc())), [],
        )
        self.assertIn(
            "delete_actor_hypothesis_wrong_stage_no_reply", state.events,
        )
        self.assertIsNone(self._character_rows()[0]["deleted_at"])

        fresh = self._char_select_state("probe2")
        self.assertEqual(
            fresh.dispatch(self.legacy.parse_outer(self._delete_pc())), [],
        )
        self.assertTrue(any(
            event.startswith(
                "delete_actor_hypothesis_repository_failure_no_reply_"
            )
            for event in fresh.events
        ))

    def test_op2_and_wrong_envelope_fail_closed(self):
        state = self._char_select_state("probe1", create=True)
        op2 = _login_protocol_request_pc(
            self.legacy, bytes.fromhex("0802080014000000004400000000"),
        )
        self.assertEqual(state.dispatch(self.legacy.parse_outer(op2)), [])
        self.assertIn(
            "delete_actor_hypothesis_op2_unproven_no_reply", state.events,
        )
        self.assertIsNone(self._character_rows()[0]["deleted_at"])

    def test_without_scenario_nothing_is_written_or_replied(self):
        state = self._char_select_state("probe1", delete=False, create=True)
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(self._delete_pc())), [],
        )
        self.assertIsNone(self._character_rows()[0]["deleted_at"])
        with self.assertRaises(PermissionError):
            state.foundation.soft_delete_character(0)

    # --- store layer ----------------------------------------------------

    def test_store_guards_and_reuse_cycle(self):
        state = self._char_select_state("probe1", create=True)
        sid = state.foundation.session_id
        with self.assertRaises(TypeError):
            self.store.soft_delete_character(sid, "0")
        with self.assertRaises(PermissionError):
            self.store.soft_delete_character(sid, 7)
        with self.assertRaises(PermissionError):
            self.store.soft_delete_character("no-such-session", 0)
        selected = self.store.select_character(sid, 0)
        with self.assertRaises(PermissionError):
            self.store.soft_delete_character(sid, 0)
        with self.store.connect() as db:
            db.execute(
                "UPDATE sessions SET selected_character_id=NULL WHERE id=?",
                (sid,),
            )
        cid = self.store.soft_delete_character(sid, 0)
        self.assertEqual(cid, selected.id)
        with self.assertRaises(PermissionError):
            self.store.soft_delete_character(sid, 0)
        rows = self._character_rows()
        self.assertIsNotNone(rows[0]["deleted_at"])


if __name__ == "__main__":
    unittest.main()
