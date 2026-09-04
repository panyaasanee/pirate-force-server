"""CORE-REQUEST of pf_bridge/notes_to_chief/20260904_1120 (LANE-UI, round
`p7m2wq`) -- eight friend/mail/party/trade vitals whose opcode and every
field are PROVEN-tier resolved, wired onto the real dispatcher.

Mirrors tests/test_lane_a_navigationex_enter_instance_dispatch_wiring.py,
which proves the identical shape (count, fire a report-only lane_hooks
point, answer nothing) for `NAVIGATIONEX_ENTER_INSTANCE_VITAL_ID`.  This
file covers all eight new branches in `runtime.py`'s
`_FRIEND_MAIL_PARTY_TRADE_DISPATCH` table in one place rather than eight
near-identical files, because the branches themselves are one shared loop,
not eight separate `if` blocks.

NOT PROVEN HERE: that a real client has ever sent any of these eight frames
to this server (PF_FIELD_VALIDATION.tsv: NOT_OBSERVED for all eight), and
not what any of them mean -- caller/verb semantics are CALL_UNCLASSIFIED
(letter 1120 nonclaim (2)).  No lane_hooks module subscribes to any of these
eight points yet; that is LANE-UI's next round, not this one.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import (  # noqa: E402
    _FRIEND_MAIL_PARTY_TRADE_DISPATCH,
    COMMUNITY_DELETE_MAIL_VITAL_ID,
    COMMUNITY_DELETE_MAIL_VITAL_NAME,
    COMMUNITY_GET_MAIL_CONTENT_VITAL_ID,
    COMMUNITY_GET_MAIL_CONTENT_VITAL_NAME,
    COMMUNITY_REMOVE_FRIEND_VITAL_ID,
    COMMUNITY_REMOVE_FRIEND_VITAL_NAME,
    COMMUNITY_REQUEST_BE_FRIEND_VITAL_ID,
    COMMUNITY_REQUEST_BE_FRIEND_VITAL_NAME,
    COMMUNITY_SEND_MAIL_VITAL_ID,
    COMMUNITY_SEND_MAIL_VITAL_NAME,
    PARTY_CMD_VITAL_ID,
    PARTY_CMD_VITAL_NAME,
    PARTY_INVITE_VITAL_ID,
    PARTY_INVITE_VITAL_NAME,
    TRADE_INVITE_VITAL_ID,
    TRADE_INVITE_VITAL_NAME,
    make_state_class,
)
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

NAME_BY_ID = {
    PARTY_INVITE_VITAL_ID: PARTY_INVITE_VITAL_NAME,
    PARTY_CMD_VITAL_ID: PARTY_CMD_VITAL_NAME,
    COMMUNITY_REQUEST_BE_FRIEND_VITAL_ID: COMMUNITY_REQUEST_BE_FRIEND_VITAL_NAME,
    COMMUNITY_REMOVE_FRIEND_VITAL_ID: COMMUNITY_REMOVE_FRIEND_VITAL_NAME,
    COMMUNITY_SEND_MAIL_VITAL_ID: COMMUNITY_SEND_MAIL_VITAL_NAME,
    COMMUNITY_GET_MAIL_CONTENT_VITAL_ID: COMMUNITY_GET_MAIL_CONTENT_VITAL_NAME,
    COMMUNITY_DELETE_MAIL_VITAL_ID: COMMUNITY_DELETE_MAIL_VITAL_NAME,
    TRADE_INVITE_VITAL_ID: TRADE_INVITE_VITAL_NAME,
}


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _synthetic_pc(legacy, nested_id: int, payload: bytes) -> bytes:
    """Identical outer-envelope shape to the NavigationEx sibling test's
    `_synthetic_enter_instance_pc`, nested id swapped per class."""
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 0x02)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, nested_id)
        + legacy.u8tag(0x0B, 0)
        + payload
    )


class FriendMailPartyTradeDispatchWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
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

    def test_the_table_has_all_eight_classes_from_letter_1120(self):
        self.assertEqual(len(_FRIEND_MAIL_PARTY_TRADE_DISPATCH), 8)
        self.assertEqual(
            {vid for vid, _point in _FRIEND_MAIL_PARTY_TRADE_DISPATCH},
            set(NAME_BY_ID),
        )

    def test_every_id_is_the_registry_hash_of_its_wire_name(self):
        # Same control as the NavigationEx sibling test: TriggerVital's own
        # v141 id must fall out of the formula before trusting it on these
        # eight literals.
        def protocol_name_id(name):
            return sum((i + 1) * ord(c) for i, c in enumerate(name)) & 0xFFFF

        self.assertEqual(
            protocol_name_id("TriggerVital"), self.legacy.TRIGGER_VITAL,
        )
        for vital_id, name in NAME_BY_ID.items():
            with self.subTest(name=name):
                self.assertEqual(protocol_name_id(name), vital_id)

    def test_no_point_has_a_subscriber_yet(self):
        # This round only opens the call site (letter 1120's own scope: "not
        # business logic").  LANE-UI's hook modules land in a later round --
        # this test exists so that round's PR has to touch (and read) this
        # file, the same discipline the NavigationEx sibling test's own
        # history documents.
        registered = lane_hooks.registered_points()
        for _vital_id, point in _FRIEND_MAIL_PARTY_TRADE_DISPATCH:
            with self.subTest(point=point):
                self.assertEqual(registered.get(point, 0), 0)

    def test_each_class_dispatches_counts_and_answers_nothing(self):
        for vital_id, point in _FRIEND_MAIL_PARTY_TRADE_DISPATCH:
            with self.subTest(point=point):
                state = self._login_and_start(f"fmpt-{vital_id:04x}")
                rx_before = state.rx_frames
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    actions = state.dispatch(self.legacy.parse_outer(
                        _synthetic_pc(self.legacy, vital_id, b"\x00\x01")
                    ))
                self.assertEqual(
                    actions, [], "this call site must send nothing back",
                )
                self.assertEqual(
                    state.rx_frames, rx_before + 1,
                    "the frame must be counted, not dropped as unmatched",
                )
                self.assertNotIn("UNPARSED", stderr.getvalue())

    def test_a_subscribed_frame_fires_and_receives_the_payload_verbatim(self):
        vital_id, point = _FRIEND_MAIL_PARTY_TRADE_DISPATCH[0]
        body = b"\x12\x34\x56"
        seen = []

        @lane_hooks.hook(point)
        def _probe(session=None, payload=None):
            seen.append((session, payload))

        self.addCleanup(lane_hooks._withdraw, _probe.__module__)

        state = self._login_and_start("fmpt-sub")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, vital_id, body)
            ))

        self.assertEqual(actions, [])
        self.assertEqual(len(seen), 1)
        session, payload = seen[0]
        self.assertIs(session, state)
        self.assertEqual(payload, body)
        self.assertIsInstance(payload, bytes)
        self.assertIn("LANE_HOOK_FIRED", stderr.getvalue())

    def test_a_raising_hook_neither_kills_the_session_nor_leaks_an_answer(self):
        vital_id, point = _FRIEND_MAIL_PARTY_TRADE_DISPATCH[-1]

        @lane_hooks.hook(point)
        def _boom(session=None, payload=None):
            raise ValueError("deliberate")

        self.addCleanup(lane_hooks._withdraw, _boom.__module__)

        state = self._login_and_start("fmpt-boom")
        rx_before = state.rx_frames
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, vital_id, b"\x00")
            ))
        self.assertEqual(actions, [])
        self.assertEqual(state.rx_frames, rx_before + 1)
        console = stderr.getvalue()
        self.assertIn("ERR", console)
        self.assertIn("deliberate", console)
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, vital_id, b"\x00")
            )),
            [],
            "the session must still be usable after a raising hook",
        )

    def test_console_output_is_ascii(self):
        vital_id, point = _FRIEND_MAIL_PARTY_TRADE_DISPATCH[3]

        @lane_hooks.hook(point)
        def _quiet(session=None, payload=None):
            pass

        self.addCleanup(lane_hooks._withdraw, _quiet.__module__)

        state = self._login_and_start("fmpt-ascii")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, vital_id, b"\x00")
            ))
        stderr.getvalue().encode("ascii")


if __name__ == "__main__":
    unittest.main()
