"""LANE-GM: the chat line -> outbound ACTION half (`gm/chat_command_action.py`).

`tests/test_gm_chat_command.py` proves the READ half: a GM's chat line is
authorized, decoded and audited, and a non-GM's is not.  This file proves the
SEND half, which is the one that decides whether anything happens on screen:

1. THE SAFETY GATE IS REAL, NOT DECORATIVE.  COO-DECISION 20260830_1645
   (reaffirmed 20260830_1742) lifted the earlier lock and set
   `FORCE_POS_VITAL_VERSION_CONFIRMED = 0` on the shipped tree -- RE-129's
   measured byte, sent now that runtime.py's confirmed-write point is real.
   The withheld path this point (1) is about did not go away: with the gate
   forced SHUT (`open_the_version_gate`'s sibling below patches it back to
   `None`), a valid `/warp` from a real GM must still produce NO action and a
   named event.  GT-101 measured what an unproven vital version does to a
   real client -- modal error, connection halted, socket closed -- so "we
   composed the frame anyway and someone will notice later" is the failure
   this file exists to make impossible, and it must stay impossible whether
   the gate is shut by the shipped constant or by a test forcing it shut.
2. THE PATH ACTUALLY WORKS now that the byte is shipped.  On the unpatched
   constant, the same chat line must yield a real
   `(label, pc, frame, delay)` action whose bytes are the ForcePos frame the
   pinned composer builds.  `open_the_version_gate` below still patches in
   `UNPROVEN_TEST_VERSION` for every test that only needs SOME open gate and
   must not be read as evidence about the real client's accepted version --
   the shipped value itself is pinned separately, in `VersionGateTests`.
3. NOTHING ESCAPES.  The call site is chief's dispatch on the game-listener
   thread, shared by every player.  Every hostile session shape below must
   come back as None plus an event, never as an exception.
4. THE PERMISSION STORY SURVIVES THE NEW PATH.  A non-GM typing the exact
   command that works for a GM gets no action, no audit row, and nothing
   decoded -- the allowlist is checked before the payload is read, on this
   path too.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import commands  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import teleport_wire  # noqa: E402
from pirateforce_foundation.gm import warp_executor  # noqa: E402
from pirateforce_foundation.gm import warp_target_record  # noqa: E402
from pirateforce_foundation.gm.commands import GmCommand  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

# A value that is NOT the real one -- RE-129 has not answered.  Tests that
# need the gate open patch this in explicitly so no test can accidentally
# read as evidence about the real client's accepted version.
UNPROVEN_TEST_VERSION = 7


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
    def __init__(self, scene_id=2, x=10.0, y=20.0, z=30.0):
        self.scene_id = scene_id
        self.scene_seq = 0
        self.x = x
        self.y = y
        self.z = z


class FakeSelected:
    def __init__(self, position=None):
        self.position = position


class FakeFoundation:
    def __init__(self, selected=None):
        self.selected = selected


class FakeSession:
    """The session surface this module is allowed to touch, and nothing else.

    Deliberately not a runtime session: if this module ever starts reaching
    for something outside the surface, these tests must fail rather than
    quietly work because a real session happened to have it.

    !! THE SURFACE GREW IN ROUND `z6gu2n` AND THIS DOCSTRING IS THE RECORD OF
    IT (pf-adversary caught the first draft leaving the old wording in place
    while the module quietly read a fourth attribute).  Reads: `.token`,
    `.events`, `.foundation.selected.position`, and now
    `.foundation.selected.id` (`warp_target_record.current_character_id`).
    Writes: `.gm_last_warp_target` on an accepted warp.  Pinned by
    `SessionSurfaceTests` below, which fails on any name outside that list.
    """

    def __init__(self, token="GM_ONE", position=None):
        self.token = token
        self.events = []
        self.foundation = FakeFoundation(FakeSelected(position))


class _Case(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"
    PLAYER_ACCOUNT = "DECKHAND"

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
        # Round `gejldf`: the cross-scene half of `/warp` WRITES a config
        # file.  Every case in this file therefore has to name a throwaway
        # one -- the first run of the new routing created a real
        # `config/gm_login_scene.json` under the repo checkout, which is a
        # test writing into the tree it is testing.
        self.login_scene_config_path = self.tmp / "config" / "gm_login_scene.json"
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def act(self, session, text, **kwargs):
        kwargs.setdefault(
            "login_scene_config_path", str(self.login_scene_config_path)
        )
        return chat_command_action.make_gm_chat_command_action(
            session,
            make_chat_payload(text),
            self.legacy,
            config_path=str(self.config_path),
            log_path=str(self.log_path),
            **kwargs,
        )

    def staged_login_scenes(self):
        if not self.login_scene_config_path.exists():
            return {}
        return json.loads(
            self.login_scene_config_path.read_text(encoding="utf-8")
        ).get("gm_login_scene", {})

    def log_records(self):
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def open_the_version_gate(self):
        return mock.patch.object(
            teleport_wire,
            "FORCE_POS_VITAL_VERSION_CONFIRMED",
            UNPROVEN_TEST_VERSION,
        )

    def close_the_version_gate(self):
        """The sibling of `open_the_version_gate`, for the tests that prove
        the withheld path.  RE-129's byte shipped (COO-DECISION 20260830_1645
        / 20260830_1742), so the shipped constant no longer withholds
        anything on its own -- a test that means to exercise the withheld
        branch must say so explicitly, by patching the gate SHUT itself,
        instead of relying on what used to be the default.
        """
        return mock.patch.object(
            teleport_wire, "FORCE_POS_VITAL_VERSION_CONFIRMED", None
        )


class VersionGateTests(_Case):
    def test_the_shipped_constant_is_confirmed_at_the_re129_value(self):
        # If this ever fails without a COO-DECISION superseding
        # 20260830_1645/20260830_1742 and cited in teleport_wire.py's own
        # comment, someone changed the shipped release gate by hand.  The
        # value itself -- 0 -- is RE-129's measured byte, and it is written
        # here as a literal so a drift in either direction (back to None, or
        # to some other byte) goes red instead of silently matching whatever
        # the source currently says.
        self.assertEqual(teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED, 0)

    def test_a_valid_gm_warp_yields_no_action_while_the_gate_is_shut(self):
        # The shipped constant no longer withholds by itself (COO-DECISION
        # 20260830_1645/1742), so this test forces the gate shut to prove the
        # withheld branch still exists and still refuses to compose.
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.close_the_version_gate():
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_WARP_WITHHELD_NO_VERSION, session.events
        )

    def test_the_line_is_still_authorized_and_audited_while_withheld(self):
        # The audit half must not regress just because the send half is
        # gated: GT-127 is decided on this log.  Gate forced shut for the
        # same reason as the test above.
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.close_the_version_gate():
            self.act(session, "/warp 2 100 200")
        records = self.log_records()
        # Two rows since CORE-REQUEST-GM-032: the issued row this test has
        # always checked, plus the outcome row that says the frame was
        # withheld.  `test_gm_command_audit_outcome.py` owns the pairing
        # rules; what matters here is that the audit half did not regress.
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["command"], "warp")
        self.assertFalse(records[0]["executed"])
        self.assertEqual(records[0]["record"], commands.AUDIT_RECORD_ISSUED)
        self.assertEqual(records[1]["record"], commands.AUDIT_RECORD_OUTCOME)
        self.assertEqual(
            records[1]["outcome"],
            chat_command_action.OUTCOME_WARP_WITHHELD_NO_VERSION,
        )
        self.assertIn(
            f"{chat_command_action.EVENT_ACCEPTED_PREFIX}warp", session.events
        )


class WarpActionTests(_Case):
    def test_a_same_scene_warp_becomes_a_real_force_pos_action(self):
        session = FakeSession(position=FakePosition(scene_id=2, z=30.0))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNotNone(action)
        label, pc, frame, delay = action
        self.assertEqual(label, chat_command_action.WARP_ACTION_LABEL)
        self.assertEqual(delay, 0.0)
        self.assertIsInstance(pc, (bytes, bytearray))
        self.assertIsInstance(frame, (bytes, bytearray))

    def test_the_bytes_are_the_pinned_composers_bytes_not_new_ones(self):
        # This module must never become a second place that knows how to
        # build ForcePos: it composes through warp_executor/teleport_wire or
        # not at all.
        session = FakeSession(position=FakePosition(scene_id=2, z=30.0))
        with self.open_the_version_gate():
            _label, pc, frame, _delay = self.act(session, "/warp 2 100 200")
        expected_pc, expected_frame = teleport_wire.make_force_pos_frame(
            self.legacy, UNPROVEN_TEST_VERSION, 100.0, 200.0, 30.0
        )
        self.assertEqual(bytes(pc), bytes(expected_pc))
        self.assertEqual(bytes(frame), bytes(expected_frame))

    def test_the_z_comes_from_the_connection_not_from_a_default(self):
        # The `warp` grammar carries no elevation; inventing one (0.0, say)
        # would drop the character through the floor or into the sky.
        session = FakeSession(position=FakePosition(scene_id=2, z=-12.5))
        with self.open_the_version_gate():
            _label, _pc, frame, _delay = self.act(session, "/warp 2 1 2")
        _pc2, expected = teleport_wire.make_force_pos_frame(
            self.legacy, UNPROVEN_TEST_VERSION, 1.0, 2.0, -12.5
        )
        self.assertEqual(bytes(frame), bytes(expected))

    def test_a_cross_scene_warp_with_coordinates_now_fires_a_live_teleport(self):
        # ForcePos carries no scene id (RE-090), and that has not changed --
        # `WarpActionTests` above still proves ForcePos never crosses scenes.
        # What changed (round `fftpji`, COO-DECISION 2026-08-31T14:41+07:00,
        # `GT-106-R2` PASS) is which mechanism a CROSS-SCENE `/warp` WITH
        # coordinates uses: ~~it stages the next login~~ -- it now fires a
        # live `TeleportVital` via `legacy.make_login_teleport`, the same
        # encoder `runtime.py`'s own call sites already send.  Nothing is
        # staged for this shape any more; a real action goes out.
        session = FakeSession(position=FakePosition(scene_id=2, z=30.0))
        action = self.act(session, "/warp 278 100 200")
        self.assertIsNotNone(action)
        label, pc, frame, delay = action
        self.assertEqual(
            label, chat_command_action.WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL
        )
        self.assertIn("TELEPORT", label)
        self.assertEqual(delay, 0.0)
        expected_pc, expected_frame = self.legacy.make_login_teleport(
            278, 0, 100.0, 200.0, 30.0
        )
        self.assertEqual(bytes(pc), bytes(expected_pc))
        self.assertEqual(bytes(frame), bytes(expected_frame))
        # No config entry -- this is the one form of the old sentence that
        # really did stop being true: nothing is staged when the live path
        # fires.
        self.assertEqual({}, self.staged_login_scenes())

    def test_a_cross_scene_warp_fires_even_with_the_force_pos_gate_shut(self):
        # The two composers are gated on two different things.  ForcePos's
        # RE-129 byte has nothing to do with whether legacy.make_login_teleport
        # (already proven live by GT-106-R2, unconditionally version-4 inside
        # that constructor) may compose -- a regression that made the cross-
        # scene path depend on the ForcePos constant would silently reopen
        # the stage-only behaviour COO-DECISION 1441 replaced.
        session = FakeSession(position=FakePosition(scene_id=2, z=30.0))
        with self.close_the_version_gate():
            action = self.act(session, "/warp 278 100 200")
        self.assertIsNotNone(action)
        self.assertEqual(
            action[0], chat_command_action.WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL
        )

    def test_the_authorization_flag_is_a_named_true_citing_coo_decision_1441(self):
        self.assertIs(
            warp_executor.WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED, True
        )

    def test_flipping_the_authorization_flag_off_falls_back_to_staging(self):
        # The kill switch this constant exists to be: with it False, a
        # cross-scene warp with coordinates must fall back to EXACTLY the
        # pre-1441 behaviour (stage, no frame) rather than to a refusal or a
        # crash -- the same graceful degradation the version gates above use.
        session = FakeSession(position=FakePosition(scene_id=2))
        with mock.patch.object(
            warp_executor, "WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED", False
        ):
            action = self.act(session, "/warp 278 100 200")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_WARP_STAGED_PREFIX}278", session.events
        )
        self.assertEqual({self.GM_ACCOUNT: 278}, self.staged_login_scenes())

    def test_an_unknown_cross_scene_destination_is_refused_not_composed(self):
        session = FakeSession(position=FakePosition(scene_id=2, z=30.0))
        action = self.act(session, "/warp 999999 100 200")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_WARP_REFUSED_PREFIX}WarpExecutorError",
            session.events,
        )
        self.assertEqual({}, self.staged_login_scenes())

    def test_a_bare_cross_scene_warp_to_a_marker_scene_now_fires_live(self):
        # GM-A (R278, round jd4jqp): the shape `test_scene_only_warp_with_
        # no_coordinates_stages_and_sends_nothing` below covers is a
        # SAME-scene bare warp. This is the NEW case -- a DIFFERENT,
        # marker-backed scene, no coordinates.
        from pirateforce_foundation import world_scene_travel

        target = world_scene_travel.destination(4)
        x, y, z = world_scene_travel.spawn_position(target)
        session = FakeSession(position=FakePosition(scene_id=2, z=30.0))
        action = self.act(session, "/warp 4")
        self.assertIsNotNone(action)
        label, pc, frame, delay = action
        self.assertEqual(
            label,
            chat_command_action.WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL,
        )
        self.assertIn("TELEPORT", label)
        self.assertEqual(delay, 0.0)
        expected_pc, expected_frame = self.legacy.make_login_teleport(
            4, 0, x, y, z
        )
        self.assertEqual(bytes(pc), bytes(expected_pc))
        self.assertEqual(bytes(frame), bytes(expected_frame))
        # The z is the DESTINATION's own pinned marker z, not the GM's old
        # scene-2 z (30.0) -- this is GT-172 finding F-2's fix for this shape.
        self.assertNotEqual(z, 30.0)
        # Nothing staged: the live branch fired, same "no config entry"
        # property the with-coordinates sibling test asserts.
        self.assertEqual({}, self.staged_login_scenes())

    def test_a_bare_cross_scene_warp_to_a_markerless_scene_still_stages(self):
        # GT-182 nonclaim 4: scene 278 (n_MARKER == 0) keeps the OLD rule
        # even though world_scene_travel has A pinned spawn for it -- this
        # is the regression this round's `has_authored_entry` gate exists
        # to prevent, mirrored here at the chat-command layer (the same
        # scene id `ProductionCallShapeTests.test_the_default_argument_
        # call_stages_where_gt141_says_it_does` already pins at the
        # default-argument-call layer).
        session = FakeSession(position=FakePosition(scene_id=2))
        action = self.act(session, "/warp 278")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_WARP_STAGED_PREFIX}278", session.events
        )
        self.assertEqual({self.GM_ACCOUNT: 278}, self.staged_login_scenes())

    def test_flipping_the_authorization_flag_off_falls_back_to_staging_too(self):
        # Same kill switch WARP_CROSS_SCENE_TELEPORT's own test proves,
        # exercised on the no-coordinates sibling.
        session = FakeSession(position=FakePosition(scene_id=2))
        with mock.patch.object(
            warp_executor, "WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED", False
        ):
            action = self.act(session, "/warp 4")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_WARP_STAGED_PREFIX}4", session.events
        )
        self.assertEqual({self.GM_ACCOUNT: 4}, self.staged_login_scenes())

    def test_scene_only_warp_with_no_coordinates_stages_and_sends_nothing(self):
        # ~~Refused~~ (round `gejldf`): the bare form carries no coordinates
        # for ForcePos to put in a frame, which is exactly the case the
        # next-login override can serve -- the login path spawns at the
        # scene's own registry entry point and needs no x/y.  What has not
        # changed: no action, no frame, gate patched open or not.
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_WARP_STAGED_PREFIX}2", session.events
        )
        self.assertEqual({self.GM_ACCOUNT: 2}, self.staged_login_scenes())

    def test_a_gm_with_no_selected_character_gets_no_action(self):
        session = FakeSession(position=None)
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_WARP_NO_POSITION, session.events
        )

    def test_the_other_commands_parse_and_audit_but_send_nothing_yet(self):
        # `say` is deliberately NOT in this list any more.  Round `w8hnu9`
        # built its action path, so it sends nothing for a different and
        # louder reason -- its own version gate -- and is pinned in
        # tests/test_gm_say_action.py.  Note what `open_the_version_gate`
        # opens here: the ForcePos constant only.  A command that started
        # sending on the strength of the WARP gate would be a real defect,
        # which is why this loop keeps running with it open.
        for text, name in (
            ("/lv 5", "lv"),
            ("/item 1001 2", "item"),
            ("/npc on 7", "npc"),
            ("/spawn 42", "spawn"),
        ):
            with self.subTest(text=text):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition(scene_id=2))
                with self.open_the_version_gate():
                    action = self.act(session, text)
                self.assertIsNone(action)
                self.assertIn(
                    f"{chat_command_action.EVENT_NO_WIRE_PATH_PREFIX}{name}",
                    session.events,
                )

    def test_npc_on_a_switchable_mob_id_gets_the_measured_recompose_answer(self):
        # CORE-REQUEST-GM-041's read point (`gm_npc_toggle_recompose.
        # npc_toggle_would_recompose`) answers False for every switchable
        # mob_id today (letter 20260830_1909) -- this pins that the chat
        # route actually asks it, not a hand-picked expectation.
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/npc on 855")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_NO_WIRE_PATH_PREFIX}npc",
            session.events,
        )
        self.assertIn(
            f"{chat_command_action.EVENT_NPC_RECOMPOSE_DIAGNOSTIC_PREFIX}"
            "would_recompose_false",
            session.events,
        )

    def test_npc_on_a_non_switchable_mob_id_is_named_not_guessed(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/npc on 999999")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_NPC_RECOMPOSE_DIAGNOSTIC_PREFIX}"
            "not_switchable",
            session.events,
        )

    def test_the_diagnostic_never_alters_dispatch_when_it_blows_up(self):
        # A DIAGNOSTIC MAY NEVER ALTER DISPATCH: even if the read point
        # itself raises something unexpected, `/npc` still resolves to
        # no-wire-path, never to an exception escaping the chat route.
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate(), mock.patch.object(
            chat_command_action.gm_npc_toggle_recompose,
            "npc_toggle_would_recompose",
            side_effect=RuntimeError("boom"),
        ):
            action = self.act(session, "/npc on 855")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_NPC_RECOMPOSE_DIAGNOSTIC_PREFIX}"
            "unexpected_RuntimeError",
            session.events,
        )

    def test_a_lying_tuple_subclass_is_rejected_not_trusted(self):
        # pf-adversary (round `nbihci`): a `tuple` subclass whose real
        # storage is empty but whose overridden `__len__`/`__getitem__` lie
        # to report length 2 must not sail past the shape guard and produce
        # a `would_recompose_*` event for data that was never really there
        # -- `commands.py::_require_args_tuple`'s own `type(args) is not
        # tuple` check exists for exactly this, and this diagnostic now uses
        # the same check instead of the weaker `isinstance`.
        class Liar(tuple):
            def __len__(self):
                return 2

            def __getitem__(self, index):
                return "on" if index == 0 else "855"

        session = FakeSession(position=FakePosition(scene_id=2))
        chat_command_action._note_npc_recompose_diagnostic(
            session, GmCommand(name="npc", args=Liar(), raw="/npc on 855")
        )
        self.assertIn(
            f"{chat_command_action.EVENT_NPC_RECOMPOSE_DIAGNOSTIC_PREFIX}"
            "bad_args_shape",
            session.events,
        )
        for event in session.events:
            self.assertNotIn("would_recompose", event)

    def test_item_with_a_single_category_id_names_that_category(self):
        # id 11 resolves in exactly one of the three item tables (measured
        # live against gm/item_catalog.py, not assumed from its docstring's
        # own examples -- id 1 and id 6 turned out ambiguous differently
        # than that docstring's illustration, which is exactly why this
        # diagnostic measures instead of guessing).
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/item 11 2")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_NO_WIRE_PATH_PREFIX}item",
            session.events,
        )
        self.assertIn(
            f"{chat_command_action.EVENT_ITEM_CATALOG_DIAGNOSTIC_PREFIX}"
            "known_quest",
            session.events,
        )

    def test_item_with_an_unknown_id_is_named_not_guessed(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/item 99999999 2")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_ITEM_CATALOG_DIAGNOSTIC_PREFIX}"
            "unknown",
            session.events,
        )

    def test_item_with_an_id_that_collides_across_categories_is_named_ambiguous(
        self,
    ):
        # id 1 resolves in two of the three tables (measured, see the
        # single-category test above) -- this is the exact shape round
        # `opr2xd` flagged as a future grammar question for chief/Panya to
        # decide, not this lane; the diagnostic names it without picking one.
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/item 1 2")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_ITEM_CATALOG_DIAGNOSTIC_PREFIX}"
            "ambiguous_2",
            session.events,
        )

    def test_item_diagnostic_never_alters_dispatch_when_it_blows_up(self):
        # Same rule as npc's own version of this test: a diagnostic that
        # raises must still resolve to no-wire-path, never escape the route.
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate(), mock.patch.object(
            chat_command_action.item_catalog,
            "item_category",
            side_effect=RuntimeError("boom"),
        ):
            action = self.act(session, "/item 11 2")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_ITEM_CATALOG_DIAGNOSTIC_PREFIX}"
            "unexpected_RuntimeError",
            session.events,
        )

    def test_item_diagnostic_rejects_a_lying_tuple_subclass(self):
        # Same threat model as npc's own version: a `tuple` subclass whose
        # overridden `__len__`/`__getitem__` lie about having 2 real
        # elements must not sail past the shape guard.
        class Liar(tuple):
            def __len__(self):
                return 2

            def __getitem__(self, index):
                return "11" if index == 0 else "2"

        session = FakeSession(position=FakePosition(scene_id=2))
        chat_command_action._note_item_catalog_diagnostic(
            session, GmCommand(name="item", args=Liar(), raw="/item 11 2")
        )
        self.assertIn(
            f"{chat_command_action.EVENT_ITEM_CATALOG_DIAGNOSTIC_PREFIX}"
            "bad_args_shape",
            session.events,
        )
        for event in session.events:
            self.assertNotIn("known_", event)
            self.assertNotIn("ambiguous_", event)

    def test_say_sends_nothing_on_the_strength_of_the_warp_gate_alone(self):
        # The two gates are independent, and this is the pin that says so:
        # opening ForcePos's constant must not make a `say` frame go out.
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/say hello")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_SAY_WITHHELD_NO_VERSION, session.events
        )


class GmprobeActionTests(_Case):
    """CORE-REQUEST-GM-043: `/gmprobe <variant_id>` -> `GM_UpdateGMStateVital`.

    Modelled on `WarpActionTests` per chief's CHIEF-REPLY (2026-08-31T03:57
    +07:00): a known variant_id becomes a real composed action, an unknown
    one is a named refusal, and -- unlike `/warp`/`/say` -- no version gate
    has to be opened first, because `GM_UPDATE_STATE_VITAL_VERSION_
    CONFIRMED` was pinned outright by RE-105 rather than starting life as
    `None`.
    """

    def test_a_known_variant_becomes_a_real_state_vital_action(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=FakePosition(scene_id=2))
        action = self.act(session, "/gmprobe baseline-all-zero")
        self.assertIsNotNone(action)
        label, pc, frame, delay = action
        self.assertEqual(label, chat_command_action.GMPROBE_ACTION_LABEL)
        self.assertEqual(delay, 0.0)
        self.assertIsInstance(pc, (bytes, bytearray))
        self.assertIsInstance(frame, (bytes, bytearray))

    def test_the_bytes_are_the_pinned_composers_bytes_not_new_ones(self):
        # This module must never become a second place that knows how to
        # build the state-vital frame: it composes through
        # bt_gm_probe/state_wire or not at all.
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=FakePosition(scene_id=2))
        _label, pc, frame, _delay = self.act(session, "/gmprobe u32-bit3")
        expected_pc, expected_frame = chat_command_action.bt_gm_probe.build_variant_frame(
            self.legacy, chat_command_action.bt_gm_probe.VARIANTS_BY_ID["u32-bit3"]
        )
        self.assertEqual(bytes(pc), bytes(expected_pc))
        self.assertEqual(bytes(frame), bytes(expected_frame))

    def test_every_named_variant_composes_without_a_version_gate_open(self):
        # No `open_the_version_gate()` context anywhere in this test --
        # that is the point being pinned: RE-105 already confirmed this
        # vital's version, so there is nothing left to gate.
        for variant_id in chat_command_action.bt_gm_probe.known_variant_ids():
            with self.subTest(variant_id=variant_id):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition(scene_id=2))
                action = self.act(session, f"/gmprobe {variant_id}")
                self.assertIsNotNone(action)

    def test_an_unknown_variant_id_is_a_named_refusal_not_a_guess(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=FakePosition(scene_id=2))
        action = self.act(session, "/gmprobe not-a-real-variant")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_GMPROBE_UNKNOWN_VARIANT, session.events
        )

    def test_the_unknown_variant_outcome_is_audited(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=FakePosition(scene_id=2))
        self.act(session, "/gmprobe not-a-real-variant")
        records = self.log_records()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["command"], "gmprobe")
        self.assertEqual(
            records[1]["outcome"],
            chat_command_action.OUTCOME_GMPROBE_UNKNOWN_VARIANT,
        )

    def test_gmprobe_needs_no_position_unlike_warp(self):
        # A probe writes GM state, not a location -- a GM with no selected
        # character (the case that refuses `/warp`) still gets a `/gmprobe`.
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=None)
        action = self.act(session, "/gmprobe baseline-all-zero")
        self.assertIsNotNone(action)

    def test_a_composer_that_explodes_is_named_not_leaked(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = FakeSession(position=FakePosition(scene_id=2))
        with mock.patch.object(
            chat_command_action.bt_gm_probe,
            "build_variant_frame",
            side_effect=RuntimeError("boom"),
        ):
            action = self.act(session, "/gmprobe baseline-all-zero")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_GMPROBE_REFUSED_PREFIX}RuntimeError",
            session.events,
        )

    def test_a_lying_tuple_subclass_is_rejected_not_trusted(self):
        # Same threat model as warp_executor/say_wire's own args-shape
        # guards: a `tuple` subclass whose real storage disagrees with its
        # overridden `__len__`/`__getitem__` must not sail past this
        # module's own shape check.
        class Liar(tuple):
            def __len__(self):
                return 1

            def __getitem__(self, index):
                raise AttributeError("gotcha")

        session = FakeSession(position=FakePosition(scene_id=2))
        outcome = chat_command.ChatCommandOutcome(
            authorized=True,
            command=GmCommand(name="gmprobe", args=Liar(), raw="/gmprobe x"),
            text="/gmprobe x",
            refusal_reason=None,
        )
        with mock.patch.object(
            chat_command_action, "handle_local_talk_chat", return_value=outcome
        ):
            action = self.act(session, "/gmprobe baseline-all-zero")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_GMPROBE_REFUSED_PREFIX}GmProbeArgsShape",
            session.events,
        )

    def test_gmprobe_parks_no_warp_target(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        self.act(session, "/gmprobe baseline-all-zero")
        self.assertIsNone(getattr(session, "gm_last_warp_target", None))


class WarpTargetRecordingTests(_Case):
    """The destination is parked for the position reader -- and only then.

    `tests/test_gm_warp_target_record.py` proves the record's own behaviour.
    What is proved HERE is the wiring: that an accepted warp parks the frame's
    own destination, that everything which sends no bytes parks nothing, and
    that a session which cannot hold a record still gets its warp.
    """

    def session_with_character(self, character_id=41, scene_id=2, z=30.0):
        session = FakeSession(position=FakePosition(scene_id=scene_id, z=z))
        session.foundation.selected.id = character_id
        return session

    def test_an_accepted_warp_parks_the_frames_own_destination(self):
        session = self.session_with_character()
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 11865.7 6147")
        self.assertIsNotNone(action)
        record = warp_target_record.take_warp_target(session, 41)
        self.assertIsNotNone(record)
        expected = struct.unpack("<f", struct.pack("<f", 11865.7))[0]
        self.assertEqual(record.target.x, expected)
        self.assertEqual(record.target.y, 6147.0)
        self.assertEqual(record.target.z, 30.0)
        self.assertEqual(record.target.scene_id, 2)
        self.assertEqual(record.character_id, 41)

    def test_the_parked_target_rebuilds_the_action_bytes_exactly(self):
        # The property the comparison rests on, checked through the real call
        # site rather than only in the record's own suite.
        session = self.session_with_character()
        with self.open_the_version_gate():
            _label, _pc, frame, _delay = self.act(session, "/warp 2 100.5 200.25")
        target = warp_target_record.take_warp_target(session, 41).target
        _pc2, expected = teleport_wire.make_force_pos_frame(
            self.legacy, UNPROVEN_TEST_VERSION, target.x, target.y, target.z
        )
        self.assertEqual(bytes(frame), bytes(expected))

    def test_a_withheld_warp_parks_nothing(self):
        # Gate forced shut (COO-DECISION 20260830_1645/1742 lifted the
        # shipped lock, so this is no longer the default): no bytes, so no
        # destination for a later position row to be measured against.
        session = self.session_with_character()
        with self.close_the_version_gate():
            self.assertIsNone(self.act(session, "/warp 2 100 200"))
        self.assertIsNone(warp_target_record.take_warp_target(session, 41))

    def test_a_refused_warp_parks_nothing(self):
        # Scene 278 is a real cross-scene destination since this round (see
        # WarpActionTests below), so this case now needs a scene id the
        # catalog genuinely does not name to stay a REFUSAL rather than a
        # composed live teleport.
        session = self.session_with_character()
        with self.open_the_version_gate():
            self.assertIsNone(self.act(session, "/warp 999999 100 200"))
        self.assertIsNone(warp_target_record.take_warp_target(session, 41))

    def test_a_gm_with_no_selected_character_parks_nothing(self):
        # The path most likely to regress: it refuses BEFORE the composer
        # runs, so a future edit that moves the parking earlier would park a
        # destination for a frame that was never built.
        session = FakeSession(position=None)
        with self.open_the_version_gate():
            self.assertIsNone(self.act(session, "/warp 2 100 200"))
        self.assertIsNone(warp_target_record.take_warp_target(session, None))

    def test_an_unreadable_character_id_still_gets_its_warp(self):
        # The id is read AFTER the frame exists.  A session whose id raises
        # must cost the comparison, never the warp.
        class Exploding:
            def __init__(self, position):
                self.position = position

            @property
            def id(self):
                raise RuntimeError("boom")

        session = FakeSession(position=FakePosition(scene_id=2, z=30.0))
        session.foundation.selected = Exploding(FakePosition(scene_id=2, z=30.0))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNotNone(action)
        self.assertNotIn(
            f"{chat_command_action.EVENT_UNEXPECTED_PREFIX}RuntimeError",
            session.events,
        )
        self.assertIsNone(
            warp_target_record.take_warp_target(
                session, warp_target_record.UNREADABLE_CHARACTER_ID
            )
        )

    def test_a_non_gm_parks_nothing(self):
        session = self.session_with_character()
        session.token = self.PLAYER_ACCOUNT
        with self.open_the_version_gate():
            self.assertIsNone(self.act(session, "/warp 2 100 200"))
        self.assertIsNone(warp_target_record.take_warp_target(session, 41))

    def test_a_say_parks_nothing_even_when_it_is_authorized(self):
        session = self.session_with_character()
        with self.open_the_version_gate():
            self.act(session, "/say hello")
        self.assertIsNone(warp_target_record.take_warp_target(session, 41))

    def test_two_warps_before_a_report_park_only_the_second(self):
        session = self.session_with_character()
        with self.open_the_version_gate():
            self.act(session, "/warp 2 100 200")
            self.act(session, "/warp 2 300 400")
        record = warp_target_record.take_warp_target(session, 41)
        self.assertEqual((record.target.x, record.target.y), (300.0, 400.0))

    def test_a_session_that_cannot_hold_a_record_still_gets_its_warp(self):
        class Sealed:
            __slots__ = ("token", "events", "foundation")

            def __init__(self, position):
                self.token = "GM_ONE"
                self.events = []
                self.foundation = FakeFoundation(FakeSelected(position))

        session = Sealed(FakePosition(scene_id=2, z=30.0))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNotNone(action)
        self.assertIn(
            chat_command_action.EVENT_WARP_TARGET_NOT_RECORDED, session.events
        )

    def test_the_not_recorded_event_is_not_read_as_a_refusal(self):
        # Consumers strip EVENT_WARP_REFUSED_PREFIX to recover an exception
        # type name, and read that family as "nothing was sent".  A warp that
        # DID send must never land in it.
        self.assertFalse(
            chat_command_action.EVENT_WARP_TARGET_NOT_RECORDED.startswith(
                chat_command_action.EVENT_WARP_REFUSED_PREFIX
            )
        )


class SessionSurfaceTests(_Case):
    """What the module may read off a session, pinned by measurement.

    The old guard was a sentence in `FakeSession`'s docstring, and round
    `z6gu2n` walked straight past it: the module started reading
    `.foundation.selected.id` and writing `.gm_last_warp_target`, and every
    test stayed green because the fake happened to allow it.  A docstring is
    not a guard; this is.
    """

    ALLOWED_ON_SESSION = {
        "token",
        "events",
        "foundation",
        "gm_last_warp_target",
        # CORE-REQUEST-GM-040, round `dm8o4l`.  READ then WRITTEN, and the
        # read is not incidental: we look first so that an unfired pairing
        # left by an earlier frame is NAMED before we overwrite it
        # (`EVENT_QUEUED_CONFIRM_OVERWROTE_PENDING`).  The value is a
        # `(action, callback)` pair; chief's append site in `runtime.py` is
        # the only reader and the only thing that clears it.  Underscore-
        # prefixed because it is a handshake between two lanes' code on one
        # session object, not part of the session's public shape.  It shows
        # up in `seen_session` through the watcher's `__setattr__` (its
        # `__getattribute__` skips underscore names), so this entry is
        # earning its place on the WRITE, which is the half that matters.
        "_gm_action_queued_confirm",
    }
    ALLOWED_ON_SELECTED = {"position", "id"}

    def test_the_module_touches_only_the_named_session_surface(self):
        seen_session = set()
        seen_selected = set()

        class Watched:
            def __init__(self, seen, **attributes):
                object.__setattr__(self, "_seen", seen)
                for name, value in attributes.items():
                    object.__setattr__(self, name, value)

            def __getattribute__(self, name):
                if not name.startswith("_"):
                    object.__getattribute__(self, "_seen").add(name)
                return object.__getattribute__(self, name)

            def __setattr__(self, name, value):
                object.__getattribute__(self, "_seen").add(name)
                object.__setattr__(self, name, value)

        selected = Watched(
            seen_selected, position=FakePosition(scene_id=2, z=30.0), id=41
        )
        session = Watched(
            seen_session,
            token=self.GM_ACCOUNT,
            events=[],
            foundation=FakeFoundation(selected),
        )
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNotNone(action)
        self.assertLessEqual(seen_session, self.ALLOWED_ON_SESSION, seen_session)
        self.assertLessEqual(seen_selected, self.ALLOWED_ON_SELECTED, seen_selected)
        # And the surface is actually exercised, or the check above is a
        # comparison against an empty set.
        self.assertIn("gm_last_warp_target", seen_session)
        self.assertIn("id", seen_selected)


class PermissionTests(_Case):
    def test_a_non_gm_typing_the_working_command_gets_no_action(self):
        session = FakeSession(token=self.PLAYER_ACCOUNT,
                              position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_REFUSED_PREFIX}{gm_dispatch.REFUSAL_NOT_GM}",
            session.events,
        )

    def test_a_non_gm_line_is_never_decoded_or_audited(self):
        session = FakeSession(token=self.PLAYER_ACCOUNT,
                              position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            self.act(session, "/warp 2 100 200")
        self.assertEqual(self.log_records(), [])
        # Nothing in the event trail may carry the sentence a player typed.
        for event in session.events:
            self.assertNotIn("warp 2 100 200", event)

    def test_ordinary_chat_from_a_gm_is_not_a_command(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "just talking to the crew")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_REFUSED_PREFIX}{chat_command.REFUSAL_NOT_A_COMMAND}",
            session.events,
        )

    def test_the_payload_can_never_name_the_account_that_is_checked(self):
        # The identity is the session's authenticated token.  A payload that
        # spells out a GM name must not promote the player who sent it.
        session = FakeSession(token=self.PLAYER_ACCOUNT,
                              position=FakePosition(scene_id=2))
        payload = make_chat_payload("/warp 2 1 2", speaker=self.GM_ACCOUNT)
        with self.open_the_version_gate():
            action = chat_command_action.make_gm_chat_command_action(
                session,
                payload,
                self.legacy,
                config_path=str(self.config_path),
                log_path=str(self.log_path),
            )
        self.assertIsNone(action)
        self.assertEqual(self.log_records(), [])


class FailClosedTests(_Case):
    """Every one of these runs on the shared game-listener thread."""

    def test_a_session_with_no_token_is_a_named_refusal_not_a_crash(self):
        class NoToken:
            def __init__(self):
                self.events = []
                self.foundation = FakeFoundation(FakeSelected(FakePosition()))

        session = NoToken()
        action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertTrue(
            any(
                event.startswith(chat_command_action.EVENT_BAD_SESSION_PREFIX)
                for event in session.events
            ),
            session.events,
        )

    def test_a_str_subclass_token_is_rejected_before_the_allowlist(self):
        # accounts.is_gm_account closes the __eq__/__hash__ bypass; this path
        # must not be the one place a subclass gets in.
        class Sneaky(str):
            def __eq__(self, other):  # pragma: no cover - must never be called
                return True

            def __hash__(self):
                return hash(str(self))

        session = FakeSession(token=Sneaky(self.PLAYER_ACCOUNT),
                              position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertEqual(self.log_records(), [])
        # Asserting the SPECIFIC event, not merely "no action": relaxing this
        # module's own `type(token) is not str` to `isinstance` still ends in
        # None (handle_local_talk_chat repeats the check and raises, which the
        # outer catch turns into an `unexpected_ValueError` event), so a test
        # that only checked for None would pass against that mutation and
        # prove nothing about the check it claims to cover.
        self.assertTrue(
            any(
                event.startswith(chat_command_action.EVENT_BAD_SESSION_PREFIX)
                for event in session.events
            ),
            session.events,
        )

    def test_a_session_whose_events_list_raises_still_returns_none(self):
        class HostileEvents(list):
            def append(self, item):
                raise RuntimeError("console is on fire")

        session = FakeSession(position=FakePosition(scene_id=2))
        session.events = HostileEvents()
        with self.open_the_version_gate():
            action = self.act(session, "not a command")
        self.assertIsNone(action)

    def test_a_session_with_no_events_attribute_at_all_still_returns_none(self):
        class Bare:
            token = "GM_ONE"
            foundation = None

        action = self.act(Bare(), "/warp 2 1 2")
        self.assertIsNone(action)

    def test_a_composer_that_explodes_is_caught_and_named(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate(), mock.patch.object(
            chat_command_action,
            "make_warp_force_pos_frame_with_target",
            side_effect=OverflowError("nope"),
        ):
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_WARP_REFUSED_PREFIX}OverflowError",
            session.events,
        )

    def test_an_exception_message_never_reaches_the_event_trail(self):
        # Exception text can embed client bytes and is a cp874 hazard on the
        # bridge console: type names only.
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate(), mock.patch.object(
            chat_command_action,
            "make_warp_force_pos_frame_with_target",
            side_effect=ValueError("ทดสอบ secret"),
        ):
            self.act(session, "/warp 2 1 2")
        for event in session.events:
            self.assertNotIn("secret", event)
            self.assertEqual(event, event.encode("ascii", "replace").decode())

    def test_an_authorization_helper_that_explodes_is_caught(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        with mock.patch.object(
            chat_command_action,
            "handle_local_talk_chat",
            side_effect=MemoryError("boom"),
        ):
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_UNEXPECTED_PREFIX}MemoryError",
            session.events,
        )

    def test_a_hand_built_command_with_a_hostile_args_shape_is_refused(self):
        # `GmCommand` is a plain frozen dataclass -- "regardless of source"
        # is the threat model warp_executor already defends; this path must
        # not be the hole.
        class Liar(tuple):
            def __len__(self):
                raise AttributeError("gotcha")

        session = FakeSession(position=FakePosition(scene_id=2))
        outcome = chat_command.ChatCommandOutcome(
            authorized=True,
            command=GmCommand(name="warp", args=Liar(), raw="/warp"),
            text="/warp",
            refusal_reason=None,
        )
        with self.open_the_version_gate(), mock.patch.object(
            chat_command_action, "handle_local_talk_chat", return_value=outcome
        ):
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)


class EventNameContractTests(_Case):
    """The event strings themselves, pinned as literals.

    pf-adversary (round `gr2q9j`) measured that every other event assertion in
    this file compares the module's output against the module's own constant,
    so renaming any constant to anything at all left the suite green -- a
    tautology, not a test.  These names are read by graders (GT entries),
    by console greps and by whoever debugs an attended boot, so they are an
    interface.  Pin them here, once, as text.
    """

    EXPECTED = {
        "EVENT_ACCEPTED_PREFIX": "gm_chat_action_accepted_",
        "EVENT_REFUSED_PREFIX": "gm_chat_action_refused_",
        "EVENT_NO_WIRE_PATH_PREFIX": "gm_chat_action_no_wire_path_",
        "EVENT_BAD_SESSION_PREFIX": "gm_chat_action_bad_session_",
        "EVENT_BAD_PAYLOAD_PREFIX": "gm_chat_action_bad_payload_",
        "EVENT_WARP_NO_POSITION": "gm_chat_action_warp_no_current_position",
        "EVENT_WARP_REFUSED_PREFIX": "gm_chat_action_warp_refused_",
        "EVENT_WARP_TARGET_NOT_RECORDED": "gm_chat_action_warp_target_not_recorded",
        "EVENT_UNEXPECTED_PREFIX": "gm_chat_action_unexpected_",
        "EVENT_WARP_WITHHELD_NO_VERSION": (
            "gm_chat_action_warp_withheld_no_confirmed_force_pos_vital_"
            "version_re129_open"
        ),
        # Round `w8hnu9`, the say action path.  pf-adversary measured that
        # without these three rows, renaming any of them left all 3941 tests
        # green -- the same missing pin that let GT-128 ship a console grep
        # for a label the code never had.
        "EVENT_SAY_WITHHELD_NO_VERSION": (
            "gm_chat_action_say_withheld_no_confirmed_gm_global_vital_"
            "version_re132_open"
        ),
        "EVENT_SAY_VERSION_CODEC_MISMATCH": (
            "gm_chat_action_say_version_codec_mismatch"
        ),
        "EVENT_SAY_REFUSED_PREFIX": "gm_chat_action_say_refused_",
        # CORE-REQUEST-GM-032: the audit's own failure names.  Pinned like
        # the rest -- an attended run that greps for the reason a warp went
        # missing must not be looking for a name a refactor renamed.
        "EVENT_OUTCOME_LOG_FAILED_PREFIX": "gm_chat_action_outcome_log_failed_",
        "EVENT_OUTCOME_NO_RECORD_ID": "gm_chat_action_outcome_no_record_id",
        "EVENT_OUTCOME_NOT_AUDITED_ACTION_WITHHELD": (
            "gm_chat_action_outcome_not_audited_action_withheld"
        ),
        "EVENT_OUTCOME_STALE_TARGET_NOT_CLEARED": (
            "gm_chat_action_outcome_stale_warp_target_not_cleared"
        ),
        # Round `gejldf`, the cross-scene half of `/warp`.
        "EVENT_WARP_STAGED_PREFIX": "gm_chat_action_warp_staged_login_scene_",
        "EVENT_WARP_STAGE_REFUSED_PREFIX": "gm_chat_action_warp_stage_refused_",
        "EVENT_OUTCOME_STAGE_NOT_REVERTED": (
            "gm_chat_action_outcome_stage_not_reverted"
        ),
        "EVENT_OUTCOME_STAGE_REVERTED": "gm_chat_action_outcome_stage_reverted",
        # Round `c48x1n`: a console line this module MEANT to write and could
        # not.  Pinned like the rest, and for this one the grep is the whole
        # point -- it is what separates "the console is broken" from "the
        # route was never wired", which an attended `GT-127` run would
        # otherwise read as the same silence.
        "EVENT_CONSOLE_WRITE_FAILED_PREFIX": (
            "gm_chat_action_console_write_failed_"
        ),
        # Round `dm8o4l`, CORE-REQUEST-GM-040: the four ways the `queued`
        # confirmation can fail to reach the ndjson.  Pinned for the same
        # reason as the audit names above -- an attended run that finds a
        # command with a `composed` row and no `queued` row has to be able
        # to grep the console for WHICH of the four happened, because they
        # mean very different things (never armed / overwritten / append
        # happened but the row would not write / someone called us twice).
        "EVENT_QUEUED_CONFIRM_NOT_ARMED_PREFIX": (
            "gm_chat_action_queued_confirm_not_armed_"
        ),
        "EVENT_QUEUED_CONFIRM_OVERWROTE_PENDING": (
            "gm_chat_action_queued_confirm_overwrote_pending"
        ),
        "EVENT_QUEUED_CONFIRM_WRITE_FAILED_PREFIX": (
            "gm_chat_action_queued_confirm_write_failed_"
        ),
        "EVENT_QUEUED_CONFIRM_FIRED_TWICE": (
            "gm_chat_action_queued_confirm_fired_twice"
        ),
        # CORE-REQUEST-GM-041's read point, wired this round: a diagnostic
        # on top of `EVENT_NO_WIRE_PATH_PREFIX` for `npc` specifically, never
        # a replacement for it.
        "EVENT_NPC_RECOMPOSE_DIAGNOSTIC_PREFIX": (
            "gm_chat_action_npc_recompose_diagnostic_"
        ),
        # GM-042 prep's read point, wired this round: same shape of
        # diagnostic on top of `EVENT_NO_WIRE_PATH_PREFIX` for `item`, never
        # a replacement for it -- see that constant's own comment above.
        "EVENT_ITEM_CATALOG_DIAGNOSTIC_PREFIX": (
            "gm_chat_action_item_catalog_diagnostic_"
        ),
        # CORE-REQUEST-GM-043: `/gmprobe <variant_id>`.  No withheld-by-
        # version-gate event exists for this command -- see
        # `_gmprobe_action`'s own docstring for why (RE-105 pinned
        # `GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED` outright, it was never a
        # `None`-until-proven gate the way `warp`/`say`'s constants are).
        "EVENT_GMPROBE_UNKNOWN_VARIANT": "gm_chat_action_gmprobe_unknown_variant",
        "EVENT_GMPROBE_REFUSED_PREFIX": "gm_chat_action_gmprobe_refused_",
    }

    # Action labels are the same kind of interface as the event names, and a
    # louder one: an attended tester greps the server console for them, and
    # `runtime.py` reads one of them as a substring.  Same pin, same reason.
    EXPECTED_LABELS = {
        "WARP_ACTION_LABEL": "LANE_GM_CHAT_WARP_TELEPORT_FORCE_POS",
        "WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL": (
            "LANE_GM_CHAT_WARP_CROSS_SCENE_TELEPORT_VITAL"
        ),
        # GM-A (`R278`, round jd4jqp): the bare-form live-teleport sibling.
        "WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL": (
            "LANE_GM_CHAT_WARP_CROSS_SCENE_NO_COORDS_TELEPORT_VITAL"
        ),
        "SAY_ACTION_LABEL": "LANE_GM_CHAT_SAY_GM_GLOBAL_MESSAGE",
        "GMPROBE_ACTION_LABEL": "LANE_GM_CHAT_GMPROBE_STATE_VITAL",
    }

    # The live hook route's names, pinned here as text for the disjointness
    # test below. These are not this lane's to change any more: chief pins the
    # same two literals against the wired call site in
    # tests/test_gm_chat_command_dispatch_wiring.py, and GT-127's headless
    # drill greps the console for them.
    LIVE_HOOK_ACCEPTED_PREFIX = "gm_chat_command_accepted_"
    LIVE_HOOK_REFUSED_PREFIX = "gm_chat_command_refused_"

    def test_every_event_name_is_the_literal_string_it_has_always_been(self):
        for name, literal in self.EXPECTED.items():
            with self.subTest(name=name):
                self.assertEqual(getattr(chat_command_action, name), literal)

    def test_every_action_label_is_the_literal_string_it_has_always_been(self):
        # GT-128 shipped a console grep for a label the code never carried,
        # and nothing caught it because no test pinned the string. Both
        # labels are pinned here now; renaming one without editing this table
        # is what an attended tester experiences as a FAIL on a working
        # system.
        for name, literal in self.EXPECTED_LABELS.items():
            with self.subTest(name=name):
                self.assertEqual(getattr(chat_command_action, name), literal)

    def test_the_two_tables_above_cover_every_name_the_module_exposes(self):
        # Without this, the tables are pinned but not COMPLETE: a new event
        # or label added next round is unpinned by default, which is exactly
        # how the say events shipped unpinned in their own first draft.
        exposed_events = {
            name for name in vars(chat_command_action) if name.startswith("EVENT_")
        }
        self.assertEqual(exposed_events, set(self.EXPECTED))
        exposed_labels = {
            name
            for name in vars(chat_command_action)
            if name.endswith("_ACTION_LABEL")
        }
        self.assertEqual(exposed_labels, set(self.EXPECTED_LABELS))

    def test_every_event_name_is_ascii_for_the_cp874_bridge_console(self):
        # The label had this test; the event strings -- which are what
        # actually reach session.events and the console exporter -- did not.
        for name in self.EXPECTED:
            value = getattr(chat_command_action, name)
            with self.subTest(name=name):
                self.assertEqual(value, value.encode("ascii").decode())

    def test_the_live_hook_route_still_emits_the_names_pinned_above(self):
        # LIVE_HOOK_*_PREFIX is a claim about a module this lane no longer
        # edits: if chief ever renames the wired route's events, the
        # disjointness test below would otherwise keep passing against a
        # string nothing emits any more.
        #
        # The first version of this test read inspect.getsource() and did an
        # `assertIn` on the TEXT. pf-adversary killed it: renaming the hook's
        # emitted literals while leaving `# was gm_chat_command_accepted_` in
        # a trailing comment kept it green while chief's own tests went red --
        # so it asserted "the string appears somewhere in the file", not "the
        # route emits it". Drive the hook and read what actually lands on
        # session.events instead.
        from pirateforce_foundation.lane_hooks import lane_gm_chat_command

        gm = FakeSession(self.GM_ACCOUNT, FakePosition())
        player = FakeSession(self.PLAYER_ACCOUNT, FakePosition())
        with mock.patch.dict(
            os.environ, {"PF_GM_ACCOUNTS_CONFIG": str(self.config_path)}
        ):
            lane_gm_chat_command._on_chat_local_talk(
                gm, make_chat_payload("/warp 2")
            )
            lane_gm_chat_command._on_chat_local_talk(
                player, make_chat_payload("/warp 2")
            )

        self.assertEqual(len(gm.events), 1, gm.events)
        self.assertTrue(
            gm.events[0].startswith(self.LIVE_HOOK_ACCEPTED_PREFIX),
            "the live hook emitted %r; this file pins %r as the accepted "
            "prefix and the disjointness test below depends on it"
            % (gm.events[0], self.LIVE_HOOK_ACCEPTED_PREFIX),
        )
        self.assertEqual(len(player.events), 1, player.events)
        self.assertTrue(
            player.events[0].startswith(self.LIVE_HOOK_REFUSED_PREFIX),
            "the live hook emitted %r; this file pins %r as the refused prefix"
            % (player.events[0], self.LIVE_HOOK_REFUSED_PREFIX),
        )

    def test_this_route_and_the_hook_route_never_share_an_event_name(self):
        # Exactly one of the two may be wired at the 0xAC52 branch, and since
        # CORE-REQUEST-GM-028 landed (runtime.py:4784) the wired one is the
        # hook. If a later commit wired both, identical event names would make
        # the double-wire look like normal operation -- one typed command
        # producing two audit rows and two rate-limit charges, indistinguish-
        # able from a GM typing twice. Distinct namespaces do not prevent
        # that; they make it legible the first time anyone reads the trail.
        for ours, theirs in (
            (chat_command_action.EVENT_ACCEPTED_PREFIX,
             self.LIVE_HOOK_ACCEPTED_PREFIX),
            (chat_command_action.EVENT_REFUSED_PREFIX,
             self.LIVE_HOOK_REFUSED_PREFIX),
        ):
            with self.subTest(ours=ours):
                self.assertNotEqual(ours, theirs)
                self.assertFalse(theirs.startswith(ours))
                self.assertFalse(ours.startswith(theirs))


class ConsoleTokenTests(_Case):
    """The console token, which had no test at all until round `vvxkft`.

    pf-adversary measured the gap: deleting the `print` outright, and renaming
    `CONSOLE_TOKEN` to `zzz_LANE_HOOK_FIRED`, both left the suite green. The
    token is WIRED-v2 evidence -- the project's rule is that a lane counts as
    wired when it EMITS on the production path, not when it imports -- so an
    untested token means a correctly wired call site and a call site chief
    never wrote produce identical console output for as long as RE-129 keeps
    the version gate shut. Three properties, each pinned separately: the
    literal, the stream, and that it is emitted at all.
    """

    def emit_one_accepted_command(self):
        session = FakeSession(self.GM_ACCOUNT, FakePosition())
        err, out = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            self.act(session, "/lv 30")
        return out.getvalue(), err.getvalue()

    def test_the_token_is_the_literal_string_it_has_always_been(self):
        self.assertEqual(
            chat_command_action.CONSOLE_TOKEN, "LANE_GM_CHAT_ACTION"
        )

    def test_the_token_is_ascii_for_the_cp874_bridge_console(self):
        value = chat_command_action.CONSOLE_TOKEN
        self.assertEqual(value, value.encode("ascii").decode())

    def test_it_differs_from_the_lane_hooks_token(self):
        # Both routes sit on the same 0xAC52 branch. A shared token would make
        # a double-wire look like one route firing twice.
        self.assertNotEqual(chat_command_action.CONSOLE_TOKEN, "LANE_HOOK_FIRED")

    def test_an_authorized_command_emits_the_token(self):
        out, err = self.emit_one_accepted_command()
        self.assertIn("LANE_GM_CHAT_ACTION", out + err)
        self.assertIn("route=action", out + err)

    def test_the_token_goes_to_stderr_and_never_to_stdout(self):
        # !! This is a regression test for a bug lane_hooks ALREADY paid for.
        # lane_hooks/__init__.py:117-123 records it: its own console token
        # went to stdout and immediately leaked one line into the JSON
        # artifact of tools/pf_runtimeres_death_headless_replay.py --json,
        # because that tool's scenario-off control dispatches a chat frame.
        # Its fix was file=sys.stderr. This route sits on the same branch,
        # which every client sends freely, so the moment
        # CORE-REQUEST-GM-029 is wired it inherits the identical exposure --
        # a stray token in the middle of a JSON document a consumer parses.
        out, err = self.emit_one_accepted_command()
        self.assertIn("LANE_GM_CHAT_ACTION", err)
        self.assertEqual(out, "")

    def test_an_ordinary_players_chat_never_reaches_the_console(self):
        # The token must not turn into one console line per player per
        # sentence: the identity check comes first, so a non-GM prints nothing.
        session = FakeSession(self.PLAYER_ACCOUNT, FakePosition())
        err, out = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            self.act(session, "/warp 2")
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn("LANE_GM_CHAT_ACTION", err.getvalue())


class OneOfTwoWiringTests(_Case):
    """Nothing in this repository could see a double-wire and refuse. Now it can.

    pf-adversary (round `vvxkft`) put the question the design had dodged:
    every artefact meant to protect the one-of-two invariant -- two event
    namespaces, the disjointness test, the console token -- makes a
    double-wire LEGIBLE, and each says in its own comment that it cannot
    PREVENT one. The invariant was held by a sentence in a request letter,
    and the last time this lane relied on chief reading a request letter,
    chief shipped the other half first and a whole round went to recovering
    from it.

    This test is the thing that acts instead of reporting. It reads the real
    runtime.py and refuses the state where both call sites exist at once.
    """

    RUNTIME = ROOT / "src/pirateforce_foundation/runtime.py"
    FIRE_POINT = '"vital_inbound_chat_local_talk"'
    ACTION_CALL = "make_gm_chat_command_action"

    def runtime_source(self):
        return self.RUNTIME.read_text(encoding="utf-8")

    def test_runtime_never_carries_both_call_sites_at_once(self):
        source = self.runtime_source()
        fired = self.FIRE_POINT in source
        called = self.ACTION_CALL in source
        self.assertFalse(
            fired and called,
            "runtime.py wires BOTH the GM-028 fire() point and the GM-029 "
            "action call at the 0xAC52 branch. CORE-REQUEST-GM-029 asks for "
            "a REPLACEMENT in one commit, not an addition: with both, every "
            "GM chat line is authorized twice, written to the ndjson audit "
            "log twice for one typed line, and charged twice against the "
            "rate limit -- the second charge being the one that silently "
            "starts refusing real commands. Delete the fire() call in the "
            "same commit that adds the action call.",
        )

    def test_exactly_one_of_the_two_is_wired_and_the_module_knows_which(self):
        # Not just "never both" -- "never neither" would silently mean the
        # chat door closed entirely. One of the two must be there.
        source = self.runtime_source()
        self.assertTrue(
            self.FIRE_POINT in source or self.ACTION_CALL in source,
            "runtime.py wires NEITHER route at the 0xAC52 branch. GT-127's "
            "gate 2 greps for the fire() point and would report BLOCKED.",
        )


class DeadGuardTests(_Case):
    """The `_current_position` guards, which no other test reaches.

    pf-adversary showed all three could be deleted with the suite still
    green.  Two are redundant with downstream validation; the `z is None`
    one is not -- it decides which event name the round emits.
    """

    def test_a_position_with_no_z_is_treated_as_absent_not_half_read(self):
        session = FakeSession(position=FakePosition(scene_id=2, z=None))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_WARP_NO_POSITION, session.events
        )

    def test_a_position_with_no_scene_id_is_treated_as_absent(self):
        session = FakeSession(position=FakePosition(scene_id=None))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_WARP_NO_POSITION, session.events
        )

    def test_a_session_with_no_foundation_is_treated_as_absent(self):
        class NoFoundation:
            token = "GM_ONE"

            def __init__(self):
                self.events = []

        session = NoFoundation()
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_WARP_NO_POSITION, session.events
        )


class ProductionCallShapeTests(_Case):
    """The three-argument call chief will actually write.

    Every other test in this file passes explicit `config_path=`/`log_path=`,
    so the shape that resolves both from CWD -- the one that decides where
    GT-127's verdict file lands -- ran zero times (pf-adversary defect 12).
    """

    def setUp(self):
        super().setUp()
        self.enterContext(
            mock.patch.dict(
                os.environ,
                {gm_accounts.ENV_OVERRIDE: str(self.config_path)},
            )
        )
        previous_cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, previous_cwd)

    def test_the_default_argument_call_stages_where_gt141_says_it_does(self):
        # The staging half has the same exposure the audit half had: every
        # other case in this file names a throwaway config, so the path an
        # attended tester actually reads -- `config/gm_login_scene.json`
        # under the server's own working directory, which is what GT-141's
        # cleanup step tells them to delete -- would otherwise run zero
        # times.  A default that resolved somewhere else would look like it
        # worked and change nothing the login path reads.
        session = FakeSession(position=FakePosition(scene_id=1))
        action = chat_command_action.make_gm_chat_command_action(
            session, make_chat_payload("/warp 278"), self.legacy
        )
        self.assertIsNone(action)
        landed = self.tmp / "config" / "gm_login_scene.json"
        self.assertTrue(landed.is_file(), sorted(p.name for p in self.tmp.iterdir()))
        self.assertEqual(
            {"gm_login_scene": {self.GM_ACCOUNT: 278}},
            json.loads(landed.read_text(encoding="utf-8")),
        )

    def test_the_default_argument_call_authorizes_and_audits(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        # Gate forced shut: this test's own subject is the withheld outcome
        # row through the default-argument path, not the version gate, but
        # since COO-DECISION 20260830_1645/1742 the shipped constant no
        # longer withholds by itself -- so the withheld state it asserts on
        # below has to be established explicitly.
        with self.close_the_version_gate():
            action = chat_command_action.make_gm_chat_command_action(
                session, make_chat_payload("/warp 2 100 200"), self.legacy
            )
        # Version gate forced shut above, so no action -- but the audit half
        # must work through the production path, because that is GT-127's
        # verdict.
        self.assertIsNone(action)
        landed = self.tmp / "capture" / "gm_command_log.ndjson"
        self.assertTrue(
            landed.is_file(),
            "the default log path resolves relative to CWD; GT-127 reads "
            "this file, so where it lands is part of the contract",
        )
        rows = [
            json.loads(line)
            for line in landed.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        # Issued row + outcome row (CORE-REQUEST-GM-032), both through the
        # default-argument production path, because that is what GT-127 reads.
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["command"], "warp")
        self.assertEqual(
            rows[1]["outcome"],
            chat_command_action.OUTCOME_WARP_WITHHELD_NO_VERSION,
        )

    def test_the_default_argument_call_refuses_a_non_gm(self):
        session = FakeSession(token=self.PLAYER_ACCOUNT,
                              position=FakePosition(scene_id=2))
        action = chat_command_action.make_gm_chat_command_action(
            session, make_chat_payload("/warp 2 100 200"), self.legacy
        )
        self.assertIsNone(action)
        self.assertFalse((self.tmp / "capture").exists())


class ContractTests(_Case):
    def test_the_label_carries_TELEPORT_because_runtime_greps_for_it(self):
        # runtime.py:3653-3660 `_move_authority_note_server_moves` reopens the
        # move-authority grace window for exactly one reason: "the action it
        # queued carries TELEPORT in its label".  Without the substring, a GM
        # warp looks to that gate like an impossible client jump; it refuses
        # the reading, and -- since the baseline only advances on admitted
        # readings -- refuses every later one too, freezing the durable row
        # for the rest of the session and persisting the pre-warp point at
        # logout.  This is a cross-module contract expressed as a substring,
        # which is exactly the kind that rots silently; pin it.
        self.assertIn("TELEPORT", chat_command_action.WARP_ACTION_LABEL)

    def test_the_cross_scene_teleport_label_carries_TELEPORT_too(self):
        # The same contract, more literally true here: this frame really is
        # a TeleportVital, and a GM crossing scenes is exactly the case
        # where a stale move-authority baseline would refuse the new
        # scene's first position report.
        self.assertIn(
            "TELEPORT", chat_command_action.WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL
        )

    def test_the_move_authority_gate_still_keys_on_that_substring(self):
        # The other half of the contract: if runtime.py ever stops keying on
        # "TELEPORT", this file should fail rather than keep asserting a rule
        # nobody enforces any more.
        source = (ROOT / "src/pirateforce_foundation/runtime.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('if action and "TELEPORT" in action[0]:', source)

    def test_the_action_shape_matches_what_runtime_appends(self):
        # runtime.py appends (label, pc, frame, delay_before) tuples; a
        # different arity would fail at the serve loop, not here.
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 1 2")
        self.assertIsInstance(action, tuple)
        self.assertEqual(len(action), 4)
        self.assertIsInstance(action[0], str)
        self.assertIsInstance(action[3], float)

    def test_the_action_label_is_ascii_for_the_cp874_bridge_console(self):
        self.assertEqual(
            chat_command_action.WARP_ACTION_LABEL,
            chat_command_action.WARP_ACTION_LABEL.encode("ascii").decode(),
        )

    def test_the_cross_scene_teleport_label_is_ascii_too(self):
        label = chat_command_action.WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL
        self.assertEqual(label, label.encode("ascii").decode())

    def test_the_cross_scene_teleport_action_shape_matches_what_runtime_appends(self):
        session = FakeSession(position=FakePosition(scene_id=2, z=30.0))
        action = self.act(session, "/warp 278 1 2")
        self.assertIsInstance(action, tuple)
        self.assertEqual(len(action), 4)
        self.assertEqual(
            action[0], chat_command_action.WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL
        )
        self.assertIsInstance(action[1], (bytes, bytearray))
        self.assertIsInstance(action[2], (bytes, bytearray))
        self.assertIsInstance(action[3], float)

    def test_the_no_coords_teleport_label_carries_TELEPORT_too(self):
        # GM-A (R278, round jd4jqp): same contract as the two labels above,
        # for the same reason -- this frame is also a real TeleportVital.
        self.assertIn(
            "TELEPORT",
            chat_command_action.WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL,
        )

    def test_the_no_coords_teleport_label_is_ascii_too(self):
        label = chat_command_action.WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL
        self.assertEqual(label, label.encode("ascii").decode())

    def test_the_no_coords_teleport_label_differs_from_its_sibling(self):
        # The whole point of a second label (see its own comment): an
        # attended tester reading the console must be able to tell "GM
        # typed x/y" from "server picked the marker spawn" apart.
        self.assertNotEqual(
            chat_command_action.WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL,
            chat_command_action.WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL,
        )

    def test_the_no_coords_teleport_action_shape_matches_what_runtime_appends(self):
        session = FakeSession(position=FakePosition(scene_id=2, z=30.0))
        action = self.act(session, "/warp 4")
        self.assertIsInstance(action, tuple)
        self.assertEqual(len(action), 4)
        self.assertEqual(
            action[0],
            chat_command_action.WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL,
        )
        self.assertIsInstance(action[1], (bytes, bytearray))
        self.assertIsInstance(action[2], (bytes, bytearray))
        self.assertIsInstance(action[3], float)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
