"""GT-193's hold: the `/speed` frame shape a real client was measured rejecting.

WHAT THIS FILE IS FOR
---------------------
Attended round R303 (2026-09-02, owner at the keyboard; results letter
`pf_bridge/notes_to_chief/20260902_1755_KA1A-R303-RESULTS-gt205-pass-gt193-
fail-gt204-full-chain-pass-and-the-pickup-path-measured-end-to-end.md`) typed
`/speed 300` on a real client for the first time.  The frame this lane built
went out -- `[G>] LANE_GM_CHAT_SPEED_UPDATE_ATTR_VITAL (74 bytes)`, carrying
`00 00 96 43` = 300.0 "followed by trailing zero fields" -- and the character
showed HP 0 and money 0 and DIED.  Afterwards: 426 inbound frames, ZERO of them
non-heartbeat.  The revive buttons produced no server traffic at all.  The
client locked itself out and the round lost it until a re-login, on a resource
(an attended hour with the owner present) this project has very little of.

The run DB was healthy throughout (`characters.speed_walk = 300.0`, hp
100/100), so nothing about the damage was persisted: the client reacted to
BYTES THIS LANE PUT ON THE WIRE.

WHAT IS PINNED HERE, AND WHAT IS DELIBERATELY NOT
-------------------------------------------------
PINNED: the production default is HELD; the hold is measured off the frame
about to be composed rather than hardcoded; it fires BEFORE the DB write; the
refusal reaches the screen like every other one; and the exact byte tail
GT-193 shipped, so a future edit that changes the shape cannot do it quietly.

NOT PINNED, BECAUSE NOBODY HAS MEASURED IT: which byte killed the character.
The tester's own nonclaim is explicit -- "I did NOT prove the client death is
caused by the trailing zero fields.  I proved the frame carries them and that
the client died on receiving it."  This file therefore asserts a CORRELATION
that earns a hold, never a root cause, and no test below is allowed to grow a
name that implies otherwise.  The question (does the client read a zero
ActorAttr mask as "change nothing" or as "zero everything", and is a body with
that section OMITTED parseable at all?) is a client-deserializer question and
belongs to LANE-RE; this round's letter to chief asks for it.

THE HOLD IS NOT A CLAIM THAT `/speed` IS WRONG.  `/speed` still parses, still
authorizes, still audits, still answers the screen.  What it no longer does is
put a shape in front of a tester that was measured, once, ending her session.
"""
from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import attr_wire  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import speed_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

RUN_COPY_DB_FILENAME = "pirateforce_lane_gm_20260902_1824.sqlite3"

# The value the owner typed in GT-193, and its f32 little-endian bytes.  Both
# spelled out rather than computed, so a change to either is visible in a diff.
GT193_TYPED_VALUE = 300.0
GT193_VALUE_BYTES = bytes((0x00, 0x00, 0x96, 0x43))
# What the tester's tally called "trailing zero fields", named exactly, from
# this clone's own composer: the ActorAttr qword mask (tag 0x32 + eight zero
# bytes) and the group-flag tag that follows it.  `cash` -- one of the fields
# that section carries (offset 0x0A8, mask 1<<11) -- is what read 0 on screen.
GT193_EMPTY_ACTOR_SECTION = bytes(
    (0x32, 0, 0, 0, 0, 0, 0, 0, 0, 0x05, 0x01)
)
GT193_BODY_LENGTH = 74


def make_chat_payload(message: str, speaker: str = "") -> bytes:
    """One inbound 0xAC52 chat payload, in the GT-006/GT-009 measured shape."""
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


class FakeSelected:
    def __init__(self, identity_lo=1, identity_hi=0, character_id=1):
        self.identity_lo = identity_lo
        self.identity_hi = identity_hi
        self.id = character_id


class FakeStore:
    """Records every write, because "was the row written?" is half the claim.

    The hold fires above the DB write, so a test that only looked at the
    returned action could not tell a held send from a send whose row moved
    first -- which is exactly the screen-disagrees-with-the-row case GT-193
    also measured (the client painted 400 after a re-login while the row held
    300, because `speed_walk` has no login read yet -- LANE-DB's own item).
    """

    def __init__(self, path):
        self.path = path
        self.calls = []
        self.stored = {}

    def read_typed_attributes(self, character_id):
        return dict(self.stored)

    def write_typed_attributes(self, character_id, values):
        self.stored.update(values)

    def write_typed_attributes_and_compose_sparse(self, character_id, values):
        self.calls.append((character_id, dict(values)))
        self.stored.update(values)
        return {
            speed_wire.SPEED_FIELD_X: float(
                values[chat_command_action.SPEED_TYPED_COLUMN]
            )
        }


class FakeLifecycle:
    def __init__(self, store):
        self.store = store


class FakeFoundation:
    def __init__(self, selected, store):
        self.selected = selected
        self.lifecycle = None if store is None else FakeLifecycle(store)


class FakeSession:
    def __init__(self, store, token="GM_ONE", selected=None):
        self.token = token
        self.events = []
        self.foundation = FakeFoundation(
            FakeSelected() if selected is None else selected, store
        )


class _Case(unittest.TestCase):
    """No `setUp` opens the hold here -- that is the whole point of this file.

    Every other speed test file opens it explicitly (their paths live below
    it).  This one runs against the shipped default, so if a future round
    flips `SPARSE_SHAPE_CLEARED_BY_A_REAL_CLIENT` without a real client behind
    it, these tests are what turns red.
    """

    GM_ACCOUNT = "GM_ONE"

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
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        # Absolute, inside this test's own temp directory: the run-copy gate
        # resolves the store path against the process CWD and fails closed,
        # and a relative `state/...` collapsed eight drivers onto one gate in
        # a sibling file (pf-adversary, round `ha492g`, D2).
        self.state_dir = self.tmp / "state"
        self.state_dir.mkdir()
        self.run_copy_db = str(self.state_dir / RUN_COPY_DB_FILENAME)

    def store(self):
        return FakeStore(self.run_copy_db)

    def session(self, store=None):
        return FakeSession(self.store() if store is None else store)

    def act(self, session, text="/speed 400"):
        return chat_command_action.make_gm_chat_command_action(
            session,
            make_chat_payload(text),
            self.legacy,
            config_path=str(self.config_path),
            log_path=str(self.log_path),
        )

    def audit_outcomes(self):
        if not self.log_path.exists():
            return []
        out = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            outcome = json.loads(line).get("outcome")
            if outcome:
                out.append(outcome)
        return out

    def opened(self):
        """A TEST-ONLY simulation of a future attended clearance."""
        return mock.patch.object(
            speed_wire, "SPARSE_SHAPE_CLEARED_BY_A_REAL_CLIENT", True
        )


class TheShippedDefaultIsHeldTests(_Case):
    def test_the_constant_on_main_is_false(self):
        self.assertIs(speed_wire.SPARSE_SHAPE_CLEARED_BY_A_REAL_CLIENT, False)

    def test_the_reader_agrees_with_the_constant(self):
        self.assertFalse(speed_wire.sparse_shape_cleared())

    def test_the_reader_is_live_not_a_snapshot(self):
        # A gate that copied the constant at import time could not be opened
        # by a future round editing one line, which is the whole contract
        # `shared_vital_version_confirmed()` already keeps for its own byte.
        with self.opened():
            self.assertTrue(speed_wire.sparse_shape_cleared())
        self.assertFalse(speed_wire.sparse_shape_cleared())

    def test_the_measurement_that_earned_the_hold_is_named_in_the_source(self):
        self.assertIn("GT-193", speed_wire.SPARSE_SHAPE_MEASURED_BY)


class TheShapeIsMeasuredNotHardcodedTests(_Case):
    def test_todays_door_announces_an_empty_actor_section(self):
        self.assertEqual(
            speed_wire.declared_empty_sections(self.legacy, 1, 0, 400.0),
            (speed_wire.SECTION_ACTOR_ATTR,),
        )

    def test_it_reports_the_other_section_when_the_field_moves(self):
        # Proof that this function MEASURES.  Point the door at an ActorAttr
        # field and the empty section becomes the BasicAttr one -- a hardcoded
        # `return ("actor_attr",)` cannot do this.
        # Not one of the two PAIRED fields (x39/x40, x41/x42 share a mask
        # bit and `encode_block` refuses half a pair by name), and the value
        # is `1` rather than `400.0` because an ActorAttr field's `kind` may
        # be an integer one -- this test is about which section comes back
        # empty, not about what any field means.
        actor_x = next(
            field[0]
            for field in attr_wire.FIELDS
            if field[1] != "basic" and field[0] not in (39, 40, 41, 42)
        )
        with mock.patch.object(speed_wire, "SPEED_FIELD_X", actor_x):
            self.assertEqual(
                speed_wire.declared_empty_sections(self.legacy, 1, 0, 1),
                (speed_wire.SECTION_BASIC_ATTR,),
            )

    def test_a_door_that_filled_both_sections_would_not_be_held(self):
        # The hold's own escape hatch, stated as a test rather than as a
        # promise in a comment: this is what "the gate opens itself for a
        # shape it was never measured against" means.
        both = mock.patch.object(
            speed_wire,
            "declared_empty_sections",
            return_value=(),
        )
        store = self.store()
        with both:
            action = self.act(self.session(store))
        self.assertEqual(action[0], chat_command_action.SPEED_ACTION_LABEL)


class TheFrameGT193ShippedTests(_Case):
    """A byte pin of the shape, so a change to it cannot happen quietly."""

    def test_it_is_still_the_seventy_four_byte_frame_the_tester_logged(self):
        # `[G>] LANE_GM_CHAT_SPEED_UPDATE_ATTR_VITAL (74 bytes)` in the R303
        # tally is the SECOND half of the composer's pair -- the one the
        # dispatcher counts -- and it is what this number pins.
        _pc, frame = speed_wire.compose_sparse_speed_update(
            self.legacy, 1, 0, GT193_TYPED_VALUE
        )
        self.assertEqual(len(bytes(frame)), GT193_BODY_LENGTH)

    def test_the_composed_frame_still_carries_the_measured_tail(self):
        pc, _frame = speed_wire.compose_sparse_speed_update(
            self.legacy, 1, 0, GT193_TYPED_VALUE
        )
        raw = bytes(pc)
        at = raw.find(GT193_VALUE_BYTES)
        self.assertNotEqual(
            at, -1, "the composed frame no longer carries 300.0 as an f32"
        )
        tail = raw[at + len(GT193_VALUE_BYTES):]
        self.assertTrue(
            tail.startswith(GT193_EMPTY_ACTOR_SECTION),
            "the bytes after the speed value are %r, not the empty ActorAttr "
            "section GT-193 measured (%r). If this door's shape changed, the "
            "hold above it has to be re-read against the new shape -- it was "
            "keyed on this one." % (tail[:16], GT193_EMPTY_ACTOR_SECTION),
        )

    def test_the_actor_mask_is_the_zero_the_tester_saw(self):
        _body, basic_mask, actor_mask = attr_wire.encode_block(
            self.legacy, 1, 0, {speed_wire.SPEED_FIELD_X: GT193_TYPED_VALUE}
        )
        self.assertNotEqual(basic_mask, 0)
        self.assertEqual(actor_mask, 0)


class TheHoldReachesTheScreenTests(_Case):
    def test_a_healthy_speed_line_is_withheld_by_default(self):
        session = self.session()
        action = self.act(session)
        self.assertIsNotNone(
            action, "a held /speed must still answer the connection"
        )
        self.assertEqual(
            action[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )

    def test_the_audit_names_the_hold(self):
        self.act(self.session())
        self.assertIn(
            chat_command_action.OUTCOME_SPEED_WITHHELD_SHAPE_UNCLEARED,
            self.audit_outcomes(),
        )

    def test_the_session_event_names_the_hold(self):
        session = self.session()
        self.act(session)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_SHAPE_UNCLEARED,
            session.events,
        )

    def test_the_outcome_has_a_console_sentence(self):
        self.assertIn(
            chat_command_action.OUTCOME_SPEED_WITHHELD_SHAPE_UNCLEARED,
            chat_command_action.NO_BYTES_BLOCKERS,
        )


class NothingMovesWhileHeldTests(_Case):
    def test_the_row_is_not_written(self):
        store = self.store()
        self.act(self.session(store))
        self.assertEqual(
            store.calls,
            [],
            "the hold fired but the row moved anyway -- a held frame plus a "
            "written row is the screen-disagrees-with-the-database case the "
            "DB-FIRST ordering exists to prevent",
        )
        self.assertEqual(store.stored, {})

    def test_the_composer_is_never_reached(self):
        store = self.store()
        with mock.patch.object(
            speed_wire,
            "compose_sparse_speed_update",
            side_effect=AssertionError("composed while held"),
        ):
            action = self.act(self.session(store))
        self.assertEqual(
            action[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )

    def test_an_unmeasurable_shape_holds_too(self):
        # Fail-closed: a composer that raises is a shape this lane cannot
        # measure, and an unmeasurable shape is not one it may ship.
        store = self.store()
        with self.opened(), mock.patch.object(
            speed_wire,
            "declared_empty_sections",
            side_effect=ValueError("cannot measure"),
        ):
            action = self.act(self.session(store))
        self.assertEqual(
            action[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )
        self.assertEqual(store.calls, [])


class TheControlTests(_Case):
    """If these fail, the tests above are proving nothing about the hold."""

    def test_the_same_line_composes_once_the_hold_is_opened(self):
        store = self.store()
        with self.opened():
            action = self.act(self.session(store))
        self.assertEqual(action[0], chat_command_action.SPEED_ACTION_LABEL)
        self.assertEqual(len(store.calls), 1)

    def test_opening_the_hold_is_the_only_difference(self):
        held_store = self.store()
        held = self.act(self.session(held_store))
        open_store = self.store()
        with self.opened():
            opened = self.act(self.session(open_store))
        self.assertNotEqual(held[0], opened[0])
