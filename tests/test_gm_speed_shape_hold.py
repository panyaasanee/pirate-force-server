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
PINNED: the production default is HELD, and held for EVERY shape (the
clearance set is empty, and a shape that merely fills both sections is not a
cleared shape -- pf-adversary D6); the signature is measured off the composer
rather than hardcoded; the refusal is answered to the connection the same way
every other refusal in this module is; and the exact byte tail GT-193 shipped,
so a future edit that changes the shape cannot do it quietly.

~~"the hold fires BEFORE the DB write"~~ -- STRUCK, and the reason is
COO-DECISION 2026-09-02T18:47+07:00 (`pf_bridge/notes_to_chief/20260902_1847_
COO-DECISION-lane-gm-stop-sending-speed-as-an-attr-frame-now.md`): "the DB
write continues as before -- the DB is already clean; what has to stop is the
outbound frame, and only that."  So this hold now stands BELOW the write, with
COO `1847`'s own deferral above it, and `NothingMovesWhileHeldTests` below
pins the new ordering instead of the old one.

THIS FILE NO LONGER TESTS THE SHIPPED DEFAULT ROUTE, and that is the biggest
thing to know before reading it.  On `main` today every `/speed` stops one
gate EARLIER than the one here, at COO `1847`'s deferral, so the tests that
exercise the shape gate through the real dispatch lift that deferral first
(`_Case.deferral_lifted`, a test-only patch).  What the shipped route does is
pinned in `tests/test_gm_speed_deferred.py`, and this file's own
`TheDeferralStandsAboveThisHoldTests` pins the ORDER of the two so neither
file can quietly become the only one that runs.

WHAT "ANSWERED TO THE CONNECTION" DOES AND DOES NOT MEAN (pf-adversary D8).
These tests assert that the action returned is the `SPEED DENIED` LocalTalk
notice and that the audit row names the hold.  That is composition inside this
process.  NOBODY HAS SEEN `SPEED DENIED` ON A SCREEN: the R303 letter this file
rests on records `SPEED DENIED count in this run = 0`, because the command
succeeded that round and no refusal path fired.  So the hold does not make
`/speed` send nothing -- it makes it send a DIFFERENT, also never-client-
observed frame, on every invocation instead of none.  That trade is the point
(the notice is one chat line; the held shape cost a character, a client and a
re-login), but it is a trade, and this file must not be read as proof that the
tester will see anything at all.

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
# Each object named, because the first draft of this file called the 74 "the
# body" and it is not (pf-adversary D7): the DBAttribute body is 30 bytes, the
# composer's first return value (`pc`, which carries the tail above) is 63, and
# the FRAME the dispatcher counts -- what the tester logged as `(74 bytes)` --
# is the second.
GT193_FRAME_LENGTH = 74


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

    Since COO `1847` the hold fires BELOW the DB write, so "was the row
    written?" is no longer the same question as "was the frame sent?" -- and
    recording the calls is what lets this file assert BOTH halves of the new
    ordering rather than inferring one from the other.  The row moving while
    the frame is held is the state GT-193 also measured from the other side
    (the client painted 400 after a re-login while the row held 300, because
    ~~`speed_walk` has no login read yet~~ -- LANE-DB's own item), and COO
    `1847` accepted it deliberately.

    !! STRUCK, NOT DELETED, by LANE-GM round `gj77z5`.  PR #605 landed that
    login read on `main`, so a re-login no longer paints 400 over a row
    holding 300 -- it paints 300.  What GT-193 measured is still what it
    measured; what changed is that the state it measured is no longer
    reachable the same way, and a reader of this file must not carry the old
    sentence forward as if it still described `main`.  The row a held
    `/speed` leaves behind now reaches the client at the next login.
    """

    def __init__(self, path):
        self.path = path
        self.calls = []
        self.stored = {}

    def read_typed_attributes(self, character_id):
        return dict(self.stored)

    def write_typed_attributes(self, character_id, values):
        self.stored.update(values)

    def write_speed_by_identity(self, identity_lo, identity_hi, speed):
        self.calls.append((identity_lo, identity_hi, speed))
        self.stored[chat_command_action.SPEED_TYPED_COLUMN] = speed
        return {speed_wire.SPEED_FIELD_X: float(speed)}


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

    def deferral_lifted(self):
        """A TEST-ONLY simulation of LANE-DB landing the `speed_walk` login read.

        COO `1847` defers every frame of this door until that read is on
        `main`, which is a gate ABOVE the one this file is about.  Tests that
        want to reach the shape gate through the real dispatch have to lift it
        first; nothing here is evidence that the login read landed, and
        `TheDeferralStandsAboveThisHoldTests` pins that the shipped default
        still stops above.
        """
        return mock.patch.object(speed_wire, "SPEED_LOGIN_READ_LANDED", True)

    def cleared(self, *shapes):
        """A TEST-ONLY simulation of a future attended clearance.

        Defaults to clearing THIS door's own signature.  Nothing that happens
        in this file is evidence about a real client.
        """
        if not shapes:
            shapes = ((speed_wire.SECTION_ACTOR_ATTR,),)
        return mock.patch.object(
            speed_wire, "SHAPES_CLEARED_BY_A_REAL_CLIENT", frozenset(shapes)
        )


class TheShippedDefaultIsHeldTests(_Case):
    def test_no_shape_is_cleared_on_main(self):
        self.assertEqual(speed_wire.SHAPES_CLEARED_BY_A_REAL_CLIENT, frozenset())

    def test_this_doors_own_shape_is_not_cleared(self):
        self.assertFalse(
            speed_wire.shape_cleared(
                speed_wire.declared_empty_sections(self.legacy, 1, 0, 400.0)
            )
        )

    def test_a_full_both_sections_shape_is_not_cleared_either(self):
        # D6: filling the section is not evidence about a client, so it is not
        # a clearance.  `()` is just another uncleared signature.
        self.assertFalse(speed_wire.shape_cleared(()))

    def test_an_unmeasurable_shape_is_never_cleared(self):
        with self.cleared((), (speed_wire.SECTION_ACTOR_ATTR,)):
            self.assertFalse(speed_wire.shape_cleared(None))

    def test_the_reader_is_live_not_a_snapshot(self):
        # A gate that copied the set at import time could not be opened by a
        # future round editing one line, which is the whole contract
        # `shared_vital_version_confirmed()` already keeps for its own byte.
        shape = speed_wire.declared_empty_sections(self.legacy, 1, 0, 400.0)
        with self.cleared():
            self.assertTrue(speed_wire.shape_cleared(shape))
        self.assertFalse(speed_wire.shape_cleared(shape))

    def test_clearing_one_shape_does_not_clear_another(self):
        with self.cleared(()):
            self.assertTrue(speed_wire.shape_cleared(()))
            self.assertFalse(
                speed_wire.shape_cleared((speed_wire.SECTION_ACTOR_ATTR,))
            )

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

    def test_a_door_that_filled_both_sections_is_still_held(self):
        """pf-adversary D6, turned into the test that would have caught it.

        The first draft of this hold opened for ANY shape with both sections
        filled, without consulting the clearance at all -- so a lane that added
        an ActorAttr field would have shipped a new, never-measured shape to an
        attended tester.  Filling the section is not evidence about a client.
        """
        store = self.store()
        with self.deferral_lifted(), mock.patch.object(
            speed_wire, "declared_empty_sections", return_value=()
        ):
            action = self.act(self.session(store))
        self.assertEqual(
            action[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )

    def test_that_same_door_sends_once_its_own_shape_is_cleared(self):
        # The control for the test above: `()` is not un-clearable, it is
        # merely uncleared.  A round that measures it clears it by name.
        store = self.store()
        with self.deferral_lifted(), mock.patch.object(
            speed_wire, "declared_empty_sections", return_value=()
        ), self.cleared(()):
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
        self.assertEqual(len(bytes(frame)), GT193_FRAME_LENGTH)

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


class TheHoldAnswersTheConnectionTests(_Case):
    """In-process composition only -- see this file's docstring, D8."""

    def test_a_healthy_speed_line_is_withheld_by_default(self):
        session = self.session()
        with self.deferral_lifted():
            action = self.act(session)
        self.assertIsNotNone(
            action, "a held /speed must still answer the connection"
        )
        self.assertEqual(
            action[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )

    def test_the_audit_names_the_hold(self):
        with self.deferral_lifted():
            self.act(self.session())
        self.assertIn(
            chat_command_action.OUTCOME_SPEED_WITHHELD_SHAPE_UNCLEARED,
            self.audit_outcomes(),
        )

    def test_the_session_event_names_the_hold(self):
        session = self.session()
        with self.deferral_lifted():
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
    """~~"nothing moves"~~ -- THE ROW MOVES NOW, by COO `1847`, and only the
    frame is held.  The class name is kept rather than renamed so a reader of
    the round that wrote it can still find it; what it pins is now the new
    ordering, stated by each test's own name.
    """

    def test_the_row_is_written_before_the_hold(self):
        store = self.store()
        with self.deferral_lifted():
            self.act(self.session(store))
        self.assertEqual(
            len(store.calls),
            1,
            "COO 1847 requires the DB write to continue as before and only "
            "the outbound frame to stop; a hold that skipped the write would "
            "leave GT-193 step 6 (diff the row) ungradeable",
        )
        self.assertEqual(
            store.stored[chat_command_action.SPEED_TYPED_COLUMN], 400.0
        )

    def test_the_composer_is_never_reached(self):
        store = self.store()
        with self.deferral_lifted(), mock.patch.object(
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
        with self.deferral_lifted(), self.cleared(), mock.patch.object(
            speed_wire,
            "declared_empty_sections",
            side_effect=ValueError("cannot measure"),
        ):
            action = self.act(self.session(store))
        self.assertEqual(
            action[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )


class TheDeferralStandsAboveThisHoldTests(_Case):
    """The ORDER of the two gates, pinned here as well as in the deferral file.

    Without this class, a future round could lift COO `1847`'s deferral and
    every test above would still pass -- they all lift it themselves.
    """

    def test_the_shipped_default_stops_at_the_deferral_not_here(self):
        session = self.session()
        self.assertIsNone(self.act(session))
        self.assertIn(chat_command_action.EVENT_SPEED_DEFERRED, session.events)
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_WITHHELD_SHAPE_UNCLEARED,
            session.events,
        )

    def test_clearing_the_shape_alone_does_not_send(self):
        # The one that matters: an attended round that measures a safe shape
        # clears it here, and the frame is STILL held, because the number it
        # would paint does not survive the next login yet.
        store = self.store()
        with self.cleared():
            self.assertIsNone(self.act(self.session(store)))

    def test_lifting_the_deferral_alone_does_not_send_either(self):
        # And the mirror: LANE-DB landing the login read does not reopen this
        # door by itself.  Two lanes, two edits, neither sufficient alone.
        store = self.store()
        with self.deferral_lifted():
            action = self.act(self.session(store))
        self.assertEqual(
            action[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )


class TheControlTests(_Case):
    """If these fail, the tests above are proving nothing about the hold."""

    def test_the_same_line_composes_once_the_shape_is_cleared(self):
        store = self.store()
        with self.deferral_lifted(), self.cleared():
            action = self.act(self.session(store))
        self.assertEqual(action[0], chat_command_action.SPEED_ACTION_LABEL)
        self.assertEqual(len(store.calls), 1)

    def test_clearing_the_shape_is_the_only_difference(self):
        held_store = self.store()
        with self.deferral_lifted():
            held = self.act(self.session(held_store))
        open_store = self.store()
        with self.deferral_lifted(), self.cleared():
            opened = self.act(self.session(open_store))
        self.assertNotEqual(held[0], opened[0])


class TheShapeDoesNotDependOnIdentityOrValueTests(_Case):
    """The pin `declared_empty_sections`'s docstring names (pf-adversary D5).

    ~~"`_speed_action` checks the shape BEFORE the store write, using the
    parsed value"~~ -- STRUCK: since COO `1847` moved both gates below the
    write, the shape is measured off `stored`, the same read-back the frame
    beneath it is composed from, so the divergence this class was written to
    make safe is no longer taken at all.

    THE PINS ARE KEPT ANYWAY, and not out of sentiment: they are what makes
    the signature a stable KEY for `SHAPES_CLEARED_BY_A_REAL_CLIENT`.  A field
    whose presence depended on the value or the identity would mean a
    clearance recorded for "the shape" was really a clearance for one call --
    which is the D6 hazard again, one level down.  These turn red first.
    """

    VALUES = (0.0, 1, 5.0, 300.0, 400.1, 400.1000061035156, -12.5, 1e30)
    IDENTITIES = ((1, 0), (0, 0), (0x11223344, 0x55667788), (7, 3))

    def test_every_value_gives_the_same_signature(self):
        first = speed_wire.declared_empty_sections(self.legacy, 1, 0, 400.0)
        for value in self.VALUES:
            with self.subTest(value=value):
                self.assertEqual(
                    speed_wire.declared_empty_sections(
                        self.legacy, 1, 0, value
                    ),
                    first,
                )

    def test_every_identity_gives_the_same_signature(self):
        first = speed_wire.declared_empty_sections(self.legacy, 1, 0, 400.0)
        for lo, hi in self.IDENTITIES:
            with self.subTest(identity=(lo, hi)):
                self.assertEqual(
                    speed_wire.declared_empty_sections(
                        self.legacy, lo, hi, 400.0
                    ),
                    first,
                )

    def test_the_typed_value_and_its_f32_readback_agree(self):
        # The exact divergence the DB-first ordering introduces: what the GM
        # typed, and what the store hands back after an f32 round trip.
        self.assertEqual(
            speed_wire.declared_empty_sections(self.legacy, 1, 0, 400.1),
            speed_wire.declared_empty_sections(
                self.legacy, 1, 0, 400.1000061035156
            ),
        )
