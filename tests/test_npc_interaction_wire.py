"""Offline guards for the npc_interaction coverage domain.

Five rows in that domain carried evidence and no test at all, which makes them
claims nobody watches. These tests cover exactly what the rows already say:

  * npc_conversation_handshake  — one click yields TargetVital plus an embedded
    ChooseNPC, and the server answers with one NPCConversation carrying one
    descriptor.
  * conversation_operation_sequence — operation 1/action 6 then operation
    2/action 1, in that order, once each, refused out of order.
  * quest_accept_and_progress — the accept path stops at the client-local
    boundary; no quest state is stored server-side.
  * shop_buy_sell — the store-5 open packet is a test harness, and nothing in
    the Foundation store implements shop inventory, prices or transactions.
  * interaction_negative_paths — the V140 P86 position is an explicit synthetic
    harness offset, not the decoded placement of that actor.

None of these tests upgrades a status. They fail if the claim drifts.
"""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.scene_load import load_scene_load_scenario
from pirateforce_foundation.session import FoundationSession, ReadOnlyFoundationSession
from pirateforce_foundation.store import SQLiteStore

ACCEPT_UI_LABEL = "V134_BOUNDED_HYPOTHESIS_Q3020_OP1_TO_ACTION6_ONCE"

# Every table the Foundation store is allowed to own today. The npc_interaction
# rows all say server-side quest, shop and reward state does not exist; this set
# is how that sentence is enforced.
EXPECTED_TABLES = {
    "schema_migrations",
    "accounts",
    "characters",
    "character_positions",
    "sessions",
    "character_backpacks",
    "character_backpack_items",
}


class NpcConversationHandshakeTests(unittest.TestCase):
    """coverage row npc_interaction/npc_conversation_handshake."""

    @classmethod
    def setUpClass(cls):
        cls.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def choose_packet(self, *, identities, lead_target=True):
        vitals = []
        if lead_target:
            vitals.append(
                self.v.u16tag(0x12, self.v.TARGET_VITAL)
                + self.v.u8tag(0x0B, 0)
                + self.v.qwordtag(0x32, identities[0])
                + self.v.u8tag(0x08, 2)
            )
        for identity in identities:
            vitals.append(
                self.v.u16tag(0x12, self.v.CHOOSE_NPC)
                + self.v.u8tag(0x0B, 0)
                + self.v.qwordtag(0x32, identity)
            )
        pc = (
            self.v.u16tag(0x12, self.v.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.v.u32tag(0x14, 0)
            + self.v.u8tag(0x08, 0)
            + self.v.u8tag(0x0B, 2)
            + self.v.u16tag(0x12, len(vitals))
            + b"".join(vitals)
        )
        return self.v.parse_outer(pc)

    def test_one_click_composition_yields_exactly_one_identity(self):
        parsed = self.choose_packet(identities=[self.v.V129_QUEST_ACTOR_ID])
        self.assertEqual(
            self.v.extract_choose_npc_identities(parsed),
            [self.v.V129_QUEST_ACTOR_ID],
        )

    def test_target_vital_alone_yields_no_identity(self):
        pc = (
            self.v.u16tag(0x12, self.v.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.v.u32tag(0x14, 0)
            + self.v.u8tag(0x08, 0)
            + self.v.u8tag(0x0B, 2)
            + self.v.u16tag(0x12, 1)
            + self.v.u16tag(0x12, self.v.TARGET_VITAL)
            + self.v.u8tag(0x0B, 0)
            + self.v.qwordtag(0x32, self.v.V129_QUEST_ACTOR_ID)
            + self.v.u8tag(0x08, 2)
        )
        self.assertEqual(
            self.v.extract_choose_npc_identities(self.v.parse_outer(pc)), []
        )

    def test_a_foreign_vital_stops_the_walk_instead_of_scanning_bytes(self):
        pc = (
            self.v.u16tag(0x12, self.v.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.v.u32tag(0x14, 0)
            + self.v.u8tag(0x08, 0)
            + self.v.u8tag(0x0B, 2)
            + self.v.u16tag(0x12, 2)
            + self.v.u16tag(0x12, self.v.TARGET_VITAL)
            + self.v.u8tag(0x0B, 0)
            + self.v.qwordtag(0x32, self.v.V129_QUEST_ACTOR_ID)
            + self.v.u8tag(0x08, 2)
            + self.v.u16tag(0x12, self.v.SHOW_MESSAGE_VITAL)
            + self.v.u8tag(0x0B, 0)
            + self.v.qwordtag(0x32, self.v.V129_QUEST_ACTOR_ID)
        )
        self.assertEqual(
            self.v.extract_choose_npc_identities(self.v.parse_outer(pc)), []
        )

    def test_empty_conversation_is_identity_plus_zero_entries(self):
        pc, frame = self.v.make_npc_conversation_empty(0x2001)
        vital = self.v.u16tag(0x12, self.v.NPC_CONVERSATION) + self.v.u8tag(0x0B, 0)
        self.assertEqual(pc.count(vital), 1)
        body = pc[pc.index(vital) + len(vital):]
        self.assertEqual(
            body,
            self.v.qwordtag(0x32, 0x2001)
            + self.v.u16tag(0x0F, 0)
            + self.v.u8tag(0x0B, 0),
        )
        self.assertEqual(frame, self.v.frame_pc(pc))

    def test_quest_conversation_carries_exactly_one_descriptor(self):
        pc, _ = self.v.make_npc_conversation_quest3020()
        vital = self.v.u16tag(0x12, self.v.NPC_CONVERSATION) + self.v.u8tag(0x0B, 0)
        body = pc[pc.index(vital) + len(vital):]
        self.assertEqual(
            body,
            self.v.qwordtag(0x32, self.v.V129_QUEST_ACTOR_ID)
            + self.v.u16tag(0x0F, 1)
            + self.v.u16tag(0x12, self.v.V129_QUEST_ID)
            + self.v.u8tag(0x08, 0)
            + self.v.u8tag(0x0B, 0),
        )

    def test_quest_conversation_refuses_any_actor_other_than_p0(self):
        for identity in (0x2000, 0x2002, self.v.V139_P86_ACTOR_ID):
            with self.assertRaises(ValueError):
                self.v.make_npc_conversation_quest3020(identity)


class ConversationOperationSequenceTests(unittest.TestCase):
    """coverage row npc_interaction/conversation_operation_sequence."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db = Path(self.tmp.name) / "npc.sqlite3"
        self.store = SQLiteStore(db, ROOT / "migrations")
        self.store.migrate()
        self.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.projector = LegacyProjector(self.v)
        default = Position(
            1, 0, self.v.V135_PLAYER_X, self.v.V135_PLAYER_Y, self.v.V135_PLAYER_Z
        )
        self.lifecycle = CharacterLifecycle(
            self.store, default, self.v.extract_avatar_attr_wire_from_actor
        )
        seed = FoundationSession(self.lifecycle, self.projector, "npc-user")
        actor = self.v.get_preset_actor_wire().replace(
            self.v.wstr_tag("test01"), self.v.wstr_tag("Arena01"), 1
        )
        self.character, _ = seed.create("Arena01", actor)
        self.scenario = load_scene_load_scenario(
            ROOT / "scenarios/scene2_fighting_fish_soldier.json"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def state(self, *, conversation_sent):
        factory = lambda token: ReadOnlyFoundationSession(
            self.store, self.projector, token, self.scenario
        )
        state = make_state_class(
            self.v,
            self.lifecycle,
            self.projector,
            scene_load_scenario=self.scenario,
            session_factory=factory,
        )("npc-user")
        state.dispatch(self.v.parse_outer(self.v._synthetic_client_login_pc()))
        state.dispatch(
            self.v.parse_outer(
                self.v._synthetic_start_game_pc(self.character.selector)
            )
        )
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        state.quest3020_conversation_sent = conversation_sent
        return state

    def quest_request(self, operation, *, quest_id=None, version=3):
        quest_id = self.v.V129_QUEST_ID if quest_id is None else quest_id
        body = (
            self.v.u16tag(0x12, quest_id)
            + self.v.u8tag(0x08, operation)
            + self.v.u8tag(0x08, 0)
            + self.v.u32tag(0x14, 0)
            + self.v.qwordtag(0x32, 0)
            + self.v.u8tag(0x05, 0)
        )
        pc = (
            self.v.u16tag(0x12, self.v.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.v.u32tag(0x14, 0)
            + self.v.u8tag(0x08, 0)
            + self.v.u8tag(0x0B, 2)
            + self.v.u16tag(0x12, 1)
            + self.v.u16tag(0x12, self.v.QUEST_OPERATE_VITAL)
            + self.v.u8tag(0x0B, version)
            + body
        )
        return self.v.parse_outer(pc)

    def labels(self, state, parsed):
        return [action[0] for action in state.dispatch(parsed)]

    def test_operation1_before_the_conversation_gets_no_reply(self):
        state = self.state(conversation_sent=False)
        self.assertEqual(self.labels(state, self.quest_request(1)), [])
        self.assertFalse(state.quest3020_accept_ui_sent)
        self.assertEqual(state.quest3020_op1_capture_count, 1)

    def test_operation2_before_the_accept_ui_gets_no_reply(self):
        state = self.state(conversation_sent=True)
        self.assertEqual(self.labels(state, self.quest_request(2)), [])
        self.assertFalse(state.quest3020_accept_success_sent)

    def test_ordered_sequence_answers_action6_then_action1_once_each(self):
        state = self.state(conversation_sent=True)
        first = state.dispatch(self.quest_request(1))
        self.assertEqual([action[0] for action in first], [ACCEPT_UI_LABEL])
        self.assertEqual(
            (first[0][1], first[0][2]), self.v.make_quest3020_action6_accept_ui()
        )
        second = state.dispatch(self.quest_request(2))
        self.assertEqual(len(second), 1)
        self.assertEqual(
            (second[0][1], second[0][2]),
            self.v.make_quest3020_action1_accept_success(),
        )
        self.assertTrue(state.quest3020_accept_success_sent)

    def test_replaying_either_operation_never_answers_twice(self):
        state = self.state(conversation_sent=True)
        state.dispatch(self.quest_request(1))
        state.dispatch(self.quest_request(2))
        for operation in (1, 2, 1, 2):
            self.assertEqual(self.labels(state, self.quest_request(operation)), [])
        self.assertEqual(state.quest3020_accept_ui_sent, True)
        self.assertEqual(state.quest3020_accept_success_sent, True)

    def test_another_quest_id_or_version_is_not_the_exact_request(self):
        for kwargs in ({"quest_id": 3021}, {"version": 2}):
            state = self.state(conversation_sent=True)
            self.assertEqual(self.labels(state, self.quest_request(1, **kwargs)), [])
            self.assertFalse(state.quest3020_accept_ui_sent)

    def test_action1_is_a_result_and_is_never_offered_as_the_opening_move(self):
        # V124 proved action 1 is an acceptance result. The accept-UI offer must
        # therefore be action 6, and the two builders must not be interchangeable.
        offer, _ = self.v.make_quest3020_action6_accept_ui()
        result, _ = self.v.make_quest3020_action1_accept_success()
        self.assertNotEqual(offer, result)
        self.assertEqual(self.v.V129_QUEST_OPEN_ACCEPT_UI_ACTION, 6)
        self.assertEqual(self.v.V129_QUEST_ACCEPT_SUCCESS_ACTION, 1)
        for builder in (
            self.v.make_quest3020_action6_accept_ui,
            self.v.make_quest3020_action1_accept_success,
        ):
            with self.assertRaises(ValueError):
                builder(0x2002)


class QuestAndShopStateGuardTests(unittest.TestCase):
    """coverage rows npc_interaction/quest_accept_and_progress and shop_buy_sell.

    Both notes state that nothing is persisted or implemented server-side. If
    someone lands quest tracking, a shop inventory or a price authority, these
    guards break so the matrix has to be re-graded first.
    """

    @classmethod
    def setUpClass(cls):
        cls.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_store_schema_owns_no_quest_shop_or_reward_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "schema.sqlite3"
            store = SQLiteStore(db, ROOT / "migrations")
            store.migrate()
            import sqlite3

            connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                    if not row[0].startswith("sqlite_")
                }
            finally:
                connection.close()
        self.assertEqual(tables, EXPECTED_TABLES)

    # CORE-REQUEST-014 re-grade (chief, R192, 2026-08-27): columbus_quest_
    # dispatch.py names "quest" throughout -- it is Columbus's NPCConversation/
    # QuestOperateVital dispatch. UPDATED round e0daaa (2026-08-27 ~15:2x):
    # dispatch_columbus_quest3021() no longer always refuses -- PANYA-DECISION
    # 2026-08-27T15:25+07:00 accepted M2 without a vehicle bind, so it now
    # teleports the player to scene 17 on a real op1/3021 dispatch. It still
    # stores nothing: no quest-state row, no tracker update, no completion,
    # no reward, no persistence of "this player did the Columbus quest" --
    # the teleport is a one-shot wire effect, not quest bookkeeping. The
    # quest_accept_and_progress row's note ("no quest state is stored
    # server-side") stays true for that reason, so the matrix does not need
    # to move off in_progress for this. Allow exactly this one file for
    # exactly the word "quest" -- any OTHER word from the list, or any OTHER
    # file, still trips this guard, on purpose.
    ALLOWED_HITS = {
        "columbus_quest_dispatch.py": {"quest"},
        "runtime.py": {"quest"},
    }

    def test_no_foundation_module_implements_quest_or_shop_behavior(self):
        offenders = {}
        # Whole words only: "request" is not a quest, and "store" alone is the
        # name of the SQLite persistence module.
        words = ("quest", "shop", "store5", "price", "reward", "trade")
        for path in sorted((ROOT / "src/pirateforce_foundation").glob("*.py")):
            text = path.read_text(encoding="utf-8").lower()
            hits = {word for word in words if re.search(rf"\b{word}\b", text)}
            hits -= self.ALLOWED_HITS.get(path.name, set())
            if hits:
                offenders[path.name] = sorted(hits)
        self.assertEqual(offenders, {})

    def test_store5_open_packet_is_a_harness_with_no_product_list(self):
        pc, _ = self.v.make_trade_zoom_store5()
        vital = self.v.u16tag(0x12, self.v.TRADE_ZOOM_VITAL) + self.v.u8tag(0x0B, 2)
        body = pc[pc.index(vital) + len(vital):]
        self.assertEqual(
            body,
            self.v.u8tag(0x08, 2)
            + self.v.u8tag(0x08, 2)
            + self.v.qwordtag(0x32, 0)
            + self.v.u32tag(0x14, self.v.V112_STORE_ID)
            + self.v.wstr_tag("")
            + self.v.u16tag(0x0F, 0)
            + self.v.u8tag(0x0B, 0),
        )
        self.assertEqual(self.v.V112_STORE_ID, 5)


class InteractionNegativePathTests(unittest.TestCase):
    """coverage row npc_interaction/interaction_negative_paths.

    V140 only passed after an explicit synthetic harness position replaced the
    decoded placement of P86. These tests keep that substitution visible.
    """

    @classmethod
    def setUpClass(cls):
        cls.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_p86_identity_follows_the_index_rule(self):
        self.assertEqual(self.v.V139_P86_INDEX, 86)
        self.assertEqual(self.v.V139_P86_ACTOR_ID, 0x2000 + 86 + 1)

    def test_harness_position_is_an_explicit_offset_from_marker1(self):
        self.assertEqual(self.v.V140_P86_HARNESS_X, self.v.V137_MARKER_X + 100.0)
        self.assertEqual(self.v.V140_P86_HARNESS_Y, self.v.V137_MARKER_Y + 50.0)
        self.assertEqual(self.v.V140_P86_HARNESS_Z, self.v.V137_MARKER_Z)

    def test_harness_position_is_not_the_decoded_placement_of_p86(self):
        rows = self.v._v94_nearest_population(
            self.v.V137_MARKER_X, self.v.V137_MARKER_Y, self.v.V137_MARKER_Z
        )
        placements = {row[0]: (row[2], row[3], row[4]) for row in rows}
        self.assertIn(self.v.V139_P86_INDEX, placements)
        decoded = placements[self.v.V139_P86_INDEX]
        harness = (
            self.v.V140_P86_HARNESS_X,
            self.v.V140_P86_HARNESS_Y,
            self.v.V140_P86_HARNESS_Z,
        )
        self.assertNotEqual(decoded, harness)
        # No other decoded actor sits on the harness point either, so the
        # substitution can never be mistaken for real population data.
        self.assertNotIn(harness, set(placements.values()))

    def test_decoded_population_snapshot_never_carries_the_harness_position(self):
        _pc, _frame, rows = self.v.make_v138_marker1_population_state()
        placements = {row[0]: (row[2], row[3], row[4]) for row in rows}
        harness = (
            self.v.V140_P86_HARNESS_X,
            self.v.V140_P86_HARNESS_Y,
            self.v.V140_P86_HARNESS_Z,
        )
        self.assertNotIn(harness, set(placements.values()))

    def test_harness_snapshot_moves_only_p86(self):
        _pc, _frame, plain_rows = self.v.make_v138_marker1_population_state()
        harness_pc, _harness_frame, harness_rows = (
            self.v.make_v140_marker1_population_state()
        )
        self.assertEqual(
            [row[0] for row in plain_rows], [row[0] for row in harness_rows]
        )
        harness_xyz = b"".join(
            self.v.f32tag(value)
            for value in (
                self.v.V140_P86_HARNESS_X,
                self.v.V140_P86_HARNESS_Y,
                self.v.V140_P86_HARNESS_Z,
            )
        )
        self.assertEqual(harness_pc.count(harness_xyz), 1)


if __name__ == "__main__":
    unittest.main()
