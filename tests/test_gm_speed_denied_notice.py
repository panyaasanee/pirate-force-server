"""Every refused `/speed` says so ON SCREEN, in twelve ASCII characters.

WHO OWNS THIS FILE AND WHY IT IS A NEW ONE
------------------------------------------
COO-DECISION 2026-09-02T03:45+07:00 (`pf_bridge/notes_to_chief/20260902_0345_
COO-DECISION-speed-refusal-localtalk-via-say-wire-12-ascii.md`) ordered chief
to land "path 1" -- the composer, the call sites, AND a test proving that all
NINE refusal paths of `/speed` emit a `Channel_LocalTalkMessageVital` (0xAC52)
frame whose body is exactly `SPEED DENIED`.  `tests/test_gm_speed_action.py`
and `tests/test_gm_chat_*` are LANE-GM's zone and that lane was told, in the
same round, not to touch the two source files chief holds (COO-DECISION
`0346`); their own follow-up pins live in their files.  So this one is
chief's, self-contained on purpose: it builds its own session doubles rather
than importing a sibling test module, because a cross-test import binds this
file's fate to another lane's fixtures and to pytest's sys.path insertion.

WHAT IS PROVEN HERE, AND AT WHICH RUNG
--------------------------------------
WIRE/DB ONLY.  Every assertion below is about BYTES this server composes.
Nothing here claims a tester sees the words on a client -- that is `GT-193`'s
screen step, at the client-observable rung, and it has not run.  The reason
the length is pinned at twelve is precisely that the client-observable
evidence on this channel exists at length 12 and nowhere else (GT-006/GT-009
probe bodies `PFCHATPROBE1`/`PFCHATPROBE2`); a 5-character body was measured
SILENT, and 26 characters was never measured at all.

WHAT IT DELIBERATELY ALSO PINS
------------------------------
The two things LANE-GM measured would break if a notice were treated as the
command's own frame (`pf_bridge/notes_to_chief/20260902_0419_LANE-GM-REPLY-
CHIEF-speed-notice-two-decisions.md`): the `GM_CHAT_NO_BYTES_SENT` console
line must SURVIVE, and CORE-REQUEST-GM-040's `queued` confirmation must NOT
be armed for a sentence saying the command did nothing.
"""
from __future__ import annotations

import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import channel_message_hypothesis  # noqa: E402
from pirateforce_foundation.gm import attr_wire  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import say_wire  # noqa: E402
from pirateforce_foundation.gm import speed_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


def composer_stand_in(legacy):
    """`compose_sparse_speed_update` as it behaved before `COO-DECISION
    20260904_0345` item 2 shut it, for the CONTROL tests in this file only.

    Three tests here are controls: they exist so that "the notice path
    refuses" cannot be satisfied by a `_speed_action` that refuses
    everything.  A control needs a route that really runs, and `/speed` no
    longer has one -- the sparse `0x309A` shape zeroes 54 rows on the client
    (`RE-222` Q0, measured as `GT-218`), so the composer refuses every call
    and `attr_wire.make_update_attr_frame` refuses the shape again below it.

    This stand-in assembles the old envelope by hand from
    `attr_wire.encode_block` (still sparse-capable on purpose).  It reaches
    no socket and it does not weaken the wall: what ships is pinned by
    `tests/test_gm_speed_wire.py`, `tests/test_gm_speed_shape_hold.py` and
    `test_gm_speed_action.TheClosedDoorIsTheShippedDefaultTests`.
    """

    def _stand_in(_legacy, identity_lo, identity_hi, value):
        body, _bm, _am = attr_wire.encode_block(
            legacy, identity_lo, identity_hi,
            {speed_wire.SPEED_FIELD_X: float(value)},
        )
        payload = (
            legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, attr_wire.AC_ATTR_ID)
            + legacy.u32tag(0x14, len(body))
            + body
        )
        return legacy.make_runtime_vitals(
            [(attr_wire.UPDATE_ATTR_VITAL_ID, 0, payload)]
        )

    return _stand_in

# A run-copy-style DB name, never the canonical one: `_speed_db_is_canonical`
# refuses on the canonical filename, and that refusal is one of the nine paths
# below rather than the state every other test should start in.
RUN_COPY_DB_PATH = "state/pirateforce_gt193_20260902_0500.sqlite3"
CANONICAL_DB_PATH = "state/pirateforce.sqlite3"


def make_chat_payload(message: str, speaker: str = "") -> bytes:
    """0xAC52 payload in the GT-006/GT-009 measured shape."""
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
    """The three methods `_speed_action` and `_speed_undo` reach for."""

    def __init__(self, path=RUN_COPY_DB_PATH):
        self.path = path
        self.raises = None
        self.readback = None
        self.stored = {}

    def read_typed_attributes(self, character_id):
        return dict(self.stored)

    def write_typed_attributes(self, character_id, values):
        self.stored.update(values)

    def write_speed_by_identity(self, identity_lo, identity_hi, speed):
        if self.raises is not None:
            raise self.raises
        if getattr(self, "refuses", False):
            # `None` == the row was NOT touched, so `stored` is left alone.
            return None
        self.stored[chat_command_action.SPEED_TYPED_COLUMN] = speed
        if self.readback is not None:
            return dict(self.readback)
        return {speed_wire.SPEED_FIELD_X: float(speed)}


class _StoreWithoutPersistence:
    """A store shape that has a path but no persistence entry point."""

    def __init__(self, path=RUN_COPY_DB_PATH):
        self.path = path


class FakeLifecycle:
    def __init__(self, store):
        self.store = store


class FakeFoundation:
    def __init__(self, selected, store):
        self.selected = selected
        self.lifecycle = None if store is None else FakeLifecycle(store)


class FakeSession:
    def __init__(self, selected=None, store=None, token="GM_ONE"):
        self.token = token
        self.events = []
        self.foundation = FakeFoundation(
            FakeSelected() if selected is None else selected,
            FakeStore() if store is None else store,
        )


class _Case(unittest.TestCase):
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

        # GT-193's shape hold sits ABOVE every path this file exercises: with
        # `speed_wire.SHAPES_CLEARED_BY_A_REAL_CLIENT` empty -- the production
        # default, pinned as the default by
        # `tests/test_gm_speed_shape_hold.py` -- `/speed` never reaches the DB
        # write or the composer at all.  These tests are about what happens
        # BELOW that gate, so they clear THIS DOOR'S OWN SIGNATURE explicitly.
        # Doing so here is a TEST-ONLY simulation of a future attended
        # clearance; no client has ever accepted this frame shape.
        _shape_cleared = mock.patch.object(
            speed_wire,
            "SHAPES_CLEARED_BY_A_REAL_CLIENT",
            frozenset({(speed_wire.SECTION_ACTOR_ATTR,)}),
        )
        _shape_cleared.start()
        self.addCleanup(_shape_cleared.stop)
        # AND THE SECOND LOCK, WHICH LANDED ABOVE THAT ONE: COO-DECISION
        # 2026-09-02T18:47+07:00 defers EVERY frame of this door -- whatever
        # its shape -- until LANE-DB lands the `speed_walk` login read on
        # `main` (`speed_wire.send_deferred`).  It sits between the DB write
        # and the shape gate, so without this second patch nothing in this
        # file reaches the composer either.  Also a TEST-ONLY simulation: the
        # shipped default is pinned deferred by
        # `tests/test_gm_speed_deferred.py`, and nothing here is evidence that
        # LANE-DB's login read exists.
        _deferral_lifted = mock.patch.object(
            speed_wire, "SPEED_LOGIN_READ_LANDED", True
        )
        _deferral_lifted.start()
        self.addCleanup(_deferral_lifted.stop)

    def act(self, session, text="/speed 400"):
        """Run the whole production path, not just the handler.

        `make_gm_chat_command_action` is what `runtime.py` calls, so the nine
        paths below are exercised through the same door a real frame comes
        in by -- including the audit write and the console announcement the
        two regression pins at the bottom of this file depend on.
        """
        return chat_command_action.make_gm_chat_command_action(
            session,
            make_chat_payload(text),
            self.legacy,
            config_path=str(self.config_path),
            log_path=str(self.log_path),
        )

    def log_records(self):
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def assertIsTheDeniedNotice(self, action):
        """`action` is a `SPEED DENIED` LocalTalk notice, decoded from its own
        composed bytes rather than compared against a hand-typed frame."""
        self.assertIsNotNone(
            action,
            "a refused /speed returned no action at all, so nothing reaches "
            "the screen -- COO-DECISION 20260902_0345 path 1",
        )
        label, pc, frame, delay = action
        self.assertEqual(
            label, chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )
        self.assertEqual(delay, 0.0)
        # 🔴 THE CHANNEL ID, READ OUT OF THE BYTES.  pf-adversary (round
        # `aa9ajr`, D1) changed the composer's channel argument to the LOCKED
        # GMGlobal id and the entire suite stayed green: `decode_channel_
        # message(channel_id, payload)` ECHOES BACK the id it is handed, and
        # the payload carries none, so an assertion on `decoded.channel_id`
        # was a tautology on the constant this test passed in. The id lives
        # at pc[16:18], little-endian, and that is the only place a mutant
        # cannot follow the test.
        self.assertEqual(
            pc[16:18],
            (0xAC52).to_bytes(2, "little"),
            "the refusal notice was composed on channel 0x%04X, not "
            "0xAC52 LocalTalk. 0x9F2C GMGlobal in particular is LOCKED by "
            "COO-DECISION 20260829_0041 and this route may never reach it."
            % int.from_bytes(pc[16:18], "little"),
        )
        offset = channel_message_hypothesis.CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET
        # The payload sits between the envelope head and the RuntimeRes
        # derived-mask tail; slicing to the end of the pc would hand the
        # decoder those two trailing bytes and it refuses them by name
        # (`trailing_bytes_after_body`), which is the decoder being right.
        payload = pc[
            offset:
            len(pc) - (
                channel_message_hypothesis.CHANNEL_MESSAGE_PC_OVERHEAD - offset
            )
        ]
        decoded = channel_message_hypothesis.decode_channel_message(
            say_wire.LOCAL_TALK_CHANNEL_ID, payload
        )
        self.assertEqual(decoded.channel_id, 0xAC52)
        self.assertEqual(decoded.body, "SPEED DENIED")
        self.assertEqual(len(decoded.body), 12)
        self.assertTrue(decoded.body.isascii())
        self.assertEqual(decoded.speaker, "")
        # The frame really carries that pc, so a green decode can never be of
        # bytes that never got framed.
        self.assertEqual(frame[len(frame) - len(pc):], pc)
        return decoded


class TheNineRefusalPathsTests(_Case):
    """One test per refusal `_speed_action` can take, by construction.

    The count is not a claim about the file: `test_the_count_is_still_nine`
    below re-derives it from the source, so a tenth refusal added without a
    notice goes red here instead of shipping silent.
    """

    def test_1_canonical_db_withheld(self):
        session = FakeSession(store=FakeStore(CANONICAL_DB_PATH))
        self.assertIsTheDeniedNotice(self.act(session))
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB, session.events
        )

    def test_2_no_selected_character(self):
        session = FakeSession()
        session.foundation.selected = None
        self.assertIsTheDeniedNotice(self.act(session))
        self.assertIn(
            chat_command_action.EVENT_SPEED_NO_SELECTED_CHARACTER, session.events
        )

    def test_3_version_gate_shut(self):
        session = FakeSession()
        with mock.patch.object(
            attr_wire, "UPDATE_ATTR_VITAL_VERSION_CONFIRMED", None
        ):
            action = self.act(session)
        self.assertIsTheDeniedNotice(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_NO_VERSION, session.events
        )

    def test_4_unparseable_value(self):
        # Patched rather than typed: `commands.parse_gm_command` applies the
        # identical finite-number check at GRAMMAR time, so `/speed banana`
        # never reaches `_speed_action` at all (it is refused as
        # `command_parse_error_GmCommandParseError`, a REFUSAL OF A DIFFERENT
        # KIND that this decision does not cover -- see the note in the
        # letter to COO). This branch is the "regardless of source" backstop.
        session = FakeSession()
        with mock.patch.object(
            speed_wire,
            "parse_speed_value",
            side_effect=speed_wire.SpeedWireError("nope"),
        ):
            action = self.act(session, "/speed 5.0")
        self.assertIsTheDeniedNotice(action)
        self.assertTrue(
            any(
                event.startswith(chat_command_action.EVENT_SPEED_REFUSED_PREFIX)
                for event in session.events
            ),
            session.events,
        )

    def test_5_no_store_method(self):
        session = FakeSession(store=_StoreWithoutPersistence())
        self.assertIsTheDeniedNotice(self.act(session))
        self.assertIn(chat_command_action.EVENT_SPEED_NO_STORE, session.events)

    def test_6_no_character_id(self):
        selected = FakeSelected()
        selected.id = None
        session = FakeSession(selected=selected)
        self.assertIsTheDeniedNotice(self.act(session))
        self.assertIn(
            chat_command_action.EVENT_SPEED_NO_CHARACTER_ID, session.events
        )

    def test_7_store_raises_on_write(self):
        store = FakeStore()
        store.raises = ValueError("no such column")
        session = FakeSession(store=store)
        self.assertIsTheDeniedNotice(self.act(session))
        self.assertTrue(
            any(
                event.startswith(
                    chat_command_action.EVENT_SPEED_PERSIST_REFUSED_PREFIX
                )
                for event in session.events
            ),
            session.events,
        )

    def test_8_readback_unusable(self):
        store = FakeStore()
        store.readback = {speed_wire.SPEED_FIELD_X: "fast"}
        session = FakeSession(store=store)
        self.assertIsTheDeniedNotice(self.act(session))
        self.assertIn(
            chat_command_action.EVENT_SPEED_PERSIST_READBACK_UNUSABLE,
            session.events,
        )

    def test_9_post_commit_composer_failure(self):
        session = FakeSession()
        with mock.patch.object(
            speed_wire,
            "compose_sparse_speed_update",
            side_effect=ValueError("composer refused"),
        ):
            action = self.act(session)
        self.assertIsTheDeniedNotice(action)
        self.assertTrue(
            any(
                event.startswith(
                    chat_command_action.EVENT_SPEED_PERSIST_COMPOSE_REFUSED_PREFIX
                )
                for event in session.events
            ),
            session.events,
        )

    def test_every_refusal_goes_through_the_notice_helper(self):
        """No refusal path may build its own `_Verdict` any more.

        ~~An AST walk over `return` statements that read `call.args[0]`
        positionally~~ -- struck: pf-adversary (round `aa9ajr`, D3) added a
        tenth SILENT refusal three ways and this test stayed green for two of
        them, because a keyword-argument `_Verdict(action=None, ...)` has an
        empty `.args`, and a verdict bound to a name and returned on the next
        line is not an `ast.Call` in a `return` at all.

        Counting the two spellings in the function's own source is blind to
        neither: the legitimate `_Verdict(` calls in `_speed_action` are named
        one by one below, and every refusal reads `_speed_denied(`.

        TWO ARE LEGITIMATE SINCE COO-DECISION `20260902_1847`, not one.  That
        decision ordered `/speed` to put NO byte on the wire until LANE-DB
        lands the `speed_walk` login read -- "no byte" including the notice
        this file exists to guard -- and to answer on the CONSOLE instead
        (`SPEED DEFERRED`).  So this count rises from 1 to 2 and the identity
        of both is pinned by name in
        `tests/test_gm_speed_denied_nine_paths.py::NoRefusalMayGoOutSilent
        Tests::test_the_bare_verdicts_are_the_success_path_and_coo_1847s_
        deferral`, which walks the AST and requires the second one to return
        `None` with `OUTCOME_SPEED_DEFERRED` and a `line_printed=` argument.
        A THIRD would be the silent refusal COO `0345` closed, and this
        assertion is still what catches it.
        """
        import inspect

        source = inspect.getsource(chat_command_action._speed_action)
        body = source[source.index('"""', source.index('"""') + 3) + 3:]
        self.assertEqual(
            body.count("_Verdict("),
            2,
            "_speed_action builds a _Verdict directly somewhere other than "
            "its success path and COO 1847's deferral. Every OTHER refusal "
            "must go through _speed_denied, or it is SILENT on the client -- "
            "the exact gap COO-DECISION 20260902_0345 closed. Found %d."
            % body.count("_Verdict("),
        )
        self.assertEqual(
            body.count("_speed_denied("),
            11,
            "the number of refusal paths in _speed_action changed (%d found, "
            "11 expected). That is not a failure by itself -- add or remove a "
            "test above to match, and re-read COO-DECISION 20260902_0345, "
            "whose condition is stated over ALL refusal paths. ~~9~~ became "
            "10 in round `et2ux4`: GT-193's shape hold is a refusal like any "
            "other and goes out through the same notice.  ~~10~~ became 11 in "
            "round `ntf90h`, when the write moved onto "
            "`store.write_speed_by_identity`: that door reports its refusal "
            "as `None`, and a `None` means THE ROW IS UNTOUCHED, which no "
            "existing word on this route was allowed to say."
            % body.count("_speed_denied("),
        )

    def test_the_success_path_is_still_the_one_verdict_and_sends_the_command(self):
        # The control for the count above: if `_speed_action` ever stopped
        # composing at all, the assertion "exactly one _Verdict" would still
        # hold over a function that refuses everything.
        session = FakeSession()
        with mock.patch.object(
            speed_wire,
            "compose_sparse_speed_update",
            composer_stand_in(self.legacy),
        ):
            action = self.act(session)
        self.assertEqual(action[0], chat_command_action.SPEED_ACTION_LABEL)


class TheNoticeIsNotTheCommandsFrameTests(_Case):
    """The two regressions LANE-GM measured before this change existed."""

    def test_the_no_bytes_console_line_still_prints_for_a_refusal(self):
        session = FakeSession(store=FakeStore(CANONICAL_DB_PATH))
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            action = self.act(session)
        self.assertIsTheDeniedNotice(action)
        printed = stream.getvalue()
        self.assertIn(
            "GM_CHAT_NO_BYTES_SENT",
            printed,
            "returning a notice action deleted the server-side line half (b) "
            "of COO-DECISION 0147 depends on: `_announce_console_outcome` "
            "opens with `if sent: return`, so `sent` must mean THE COMMAND'S "
            "frame went out, never `some bytes did`. Console was: %r" % printed,
        )
        self.assertIn("withheld_speed_canonical_db", printed)

    def test_a_notice_never_arms_the_queued_confirmation(self):
        session = FakeSession(store=FakeStore(CANONICAL_DB_PATH))
        action = self.act(session)
        self.assertIsTheDeniedNotice(action)
        self.assertIsNone(
            getattr(session, "_gm_action_queued_confirm", None),
            "a refusal notice armed CORE-REQUEST-GM-040's queued "
            "confirmation. The `queued` row means this COMMAND's frame "
            "reached runtime; pairing it with a sentence that says the "
            "command did nothing makes the audit unreadable in exactly the "
            "way CORE-REQUEST-GM-032 item 1 was opened to fix.",
        )

    def test_a_command_that_really_runs_still_arms_it(self):
        # The other direction, so the fix above cannot be "never arm".
        # `/speed`'s own wire door is shut (`COO-DECISION 20260904_0345`
        # item 2), so the control composes through the stand-in -- see
        # `composer_stand_in`.
        session = FakeSession()
        with mock.patch.object(
            speed_wire,
            "compose_sparse_speed_update",
            composer_stand_in(self.legacy),
        ):
            action = self.act(session)
        self.assertIsNotNone(action)
        self.assertEqual(action[0], chat_command_action.SPEED_ACTION_LABEL)
        self.assertIsNotNone(
            getattr(session, "_gm_action_queued_confirm", None)
        )

    def test_the_audit_word_is_still_the_refusal_word(self):
        # LANE-GM letter 20260902_0419 question 2: `outcome` answers "did the
        # command have its effect?", not "did any byte leave".
        session = FakeSession(store=FakeStore(CANONICAL_DB_PATH))
        self.act(session)
        outcomes = [
            record.get("outcome")
            for record in self.log_records()
            if record.get("outcome")
        ]
        self.assertIn(
            chat_command_action.OUTCOME_SPEED_WITHHELD_CANONICAL_DB, outcomes
        )


class WhatTheNoticeDoesNotFixTests(_Case):
    """Measured limits, pinned so nobody reads the notice as wider than it is.

    Written after pf-adversary (round `aa9ajr`) found each of them.  These
    tests assert the CURRENT behaviour, and every one of them is a behaviour
    chief reported to COO rather than changed on his own: two of them are
    waiting on a ruling, and if the ruling changes the behaviour, the test
    changes with it -- that is the point of pinning them.
    """

    def test_two_paths_say_denied_while_the_row_already_holds_the_value(self):
        """D2: the screen says DENIED and the DB says 400.

        Paths 8 and 9 run AFTER `write_typed_attributes_and_compose_sparse`
        committed. `_make_action` runs the undo only when the outcome row
        cannot be written, so on a normal boot the row keeps the new value
        while the GM is told the command was refused -- the
        screen-disagrees-with-the-row case `_speed_action`'s own DB-FIRST
        comment exists to prevent, running in the mirror direction. It
        PREDATES the notice (the row behaved this way before anything went
        to the screen); what the notice adds is a claim on screen about it.
        Reported to COO in the R299 letter: either those two paths should run
        their undo, or they need their own sentence. Until that ruling, this
        is what the code does.
        """
        store = FakeStore()
        store.readback = {speed_wire.SPEED_FIELD_X: "fast"}
        session = FakeSession(store=store)
        self.assertIsTheDeniedNotice(self.act(session))
        self.assertEqual(
            store.stored,
            {chat_command_action.SPEED_TYPED_COLUMN: 400.0},
            "the row no longer keeps the committed value on a post-commit "
            "refusal. If that is deliberate (COO ruled on the R299 letter), "
            "this test records the old behaviour and should be rewritten to "
            "assert the new one -- do not simply delete it.",
        )

    def test_a_typo_still_never_says_SPEED_DENIED_it_says_TYPO_REFUSED(self):
        """D6, ANSWERED: `/speed fast` never reaches the nine paths.

        ~~"and gets no sentence ... today that is two of three"~~ -- struck,
        not deleted, because this class's own docstring says that is what
        pinning a reported behaviour is for.  `parse_gm_command` applies the
        same finite-number check at GRAMMAR time, so the commonest GM mistake
        is still refused above `_speed_action` and still takes none of the
        nine paths -- that half is unchanged and is what the label assertion
        below pins.  What changed is the ruling chief asked for in the same
        breath: COO-DECISION 2026-09-02T06:47+07:00 (`pf_bridge/notes_to_
        chief/consumed/20260902_0647_COO-DECISION-typo-layer-notice-is-TYPO-
        REFUSED-12-ascii-after-p1.md`) supplied the second 12-character
        string, `TYPO REFUSED`, for the syntax layer of EVERY command.  So
        COO-DECISION `0147`'s three states are now three different things on
        screen, and this test pins the one thing that would still be a lie:
        a mistyped command must never claim the SPEED subsystem refused it.

        The full proof of the typo layer (bytes decoded, every command name,
        the excluded refusals, `queued` never armed) lives in
        `tests/test_gm_typo_refused_notice.py`; this stays here because it is
        the boundary between the two files' subjects.
        """
        session = FakeSession()
        action = self.act(session, "/speed fast")
        self.assertIsNotNone(action)
        self.assertEqual(
            action[0], chat_command_action.TYPO_REFUSED_NOTICE_ACTION_LABEL
        )
        self.assertNotEqual(
            action[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )
        self.assertEqual(
            [
                event
                for event in session.events
                if event.startswith("gm_chat_action_speed_")
            ],
            [],
            "a mistyped /speed reached one of the nine DB-layer paths: %s"
            % session.events,
        )


class TheAuditFailureBranchTests(_Case):
    """D4: what happens on the boot where the audit log cannot be written."""

    def test_a_dropped_notice_is_named_rather_than_silently_lost(self):
        session = FakeSession(store=FakeStore(CANONICAL_DB_PATH))
        with mock.patch.object(
            chat_command_action, "_log_outcome", return_value=False
        ):
            action = self.act(session)
        self.assertIsNone(
            action,
            "a notice was returned even though its outcome row could not be "
            "written; this house does not send bytes it cannot record",
        )
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_NOT_AUDITED_NOTICE_DROPPED,
            session.events,
            "the notice was dropped with no event saying so, which makes "
            "'the GM saw nothing' and 'the sentence was built and thrown "
            "away' indistinguishable on exactly the boot where an operator "
            "is already in trouble. Events: %s" % session.events,
        )
        self.assertNotIn(
            chat_command_action.EVENT_OUTCOME_NOT_AUDITED_ACTION_WITHHELD,
            session.events,
            "a refusal notice was reported under the event that means 'a "
            "composed COMMAND frame was withheld', which is asserted with "
            "that narrower meaning elsewhere in this repo",
        )


class TheConsoleSaysTheSentenceWentOutTests(_Case):
    """The artifact that answers 'did the notice really leave the server?'.

    pf-adversary's closing question (round `aa9ajr`): `queued` is deliberately
    not armed, the no-bytes line prints for the COMMAND, and the only other
    trace was an event named `..._notice_composed` -- which is also written on
    the run where the notice is dropped. `GT-193` step 9 grades the sentence,
    so the sentence gets its own line.
    """

    def test_a_sent_notice_prints_its_own_console_line(self):
        session = FakeSession(store=FakeStore(CANONICAL_DB_PATH))
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            self.assertIsTheDeniedNotice(self.act(session))
        printed = stream.getvalue()
        self.assertIn(chat_command_action.NOTICE_CONSOLE_TOKEN, printed)
        self.assertIn("SPEED DENIED", printed)
        # Both statements are true at once and both must be printed.
        self.assertIn(chat_command_action.WITHHELD_CONSOLE_TOKEN, printed)
        self.assertTrue(printed.isascii(), repr(printed))

    def test_a_dropped_notice_does_not_print_that_line(self):
        session = FakeSession(store=FakeStore(CANONICAL_DB_PATH))
        stream = io.StringIO()
        with mock.patch.object(
            chat_command_action, "_log_outcome", return_value=False
        ):
            with contextlib.redirect_stderr(stream):
                self.act(session)
        self.assertNotIn(
            chat_command_action.NOTICE_CONSOLE_TOKEN, stream.getvalue()
        )

    def test_a_command_that_really_ran_prints_neither(self):
        session = FakeSession()
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream), mock.patch.object(
            speed_wire,
            "compose_sparse_speed_update",
            composer_stand_in(self.legacy),
        ):
            self.act(session)
        printed = stream.getvalue()
        self.assertNotIn(chat_command_action.NOTICE_CONSOLE_TOKEN, printed)
        self.assertNotIn(chat_command_action.WITHHELD_CONSOLE_TOKEN, printed)


class TheComposerIsTheOnlyDoorToTheCodecTests(_Case):
    """D1's structural half: WHICH channel id each composer may pass.

    `tests/test_gm_say_gate_lock.py` exempts `say_wire.py` wholesale from its
    "only this file may call the shared codec" rule -- an exemption granted
    when this file held exactly ONE composer whose call sites were gate
    -scanned. This round adds a second composer inside that exemption, so the
    exemption now has to be qualified, and chief qualifies it in his own file
    rather than editing another lane's lock.
    """

    def test_each_codec_call_in_say_wire_passes_its_own_channel_constant(self):
        import ast

        source = (
            ROOT / "src/pirateforce_foundation/gm/say_wire.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        allowed = {
            "make_say_broadcast_frame": "GM_GLOBAL_CHANNEL_ID",
            "make_local_talk_notice_frame": "LOCAL_TALK_CHANNEL_ID",
        }
        seen = {}
        for holder in ast.walk(tree):
            if not isinstance(holder, ast.FunctionDef):
                continue
            for node in ast.walk(holder):
                if not isinstance(node, ast.Call):
                    continue
                name = getattr(
                    node.func, "id", getattr(node.func, "attr", "")
                )
                if name != "make_channel_message_response":
                    continue
                self.assertGreaterEqual(len(node.args), 2, ast.dump(node))
                channel = node.args[1]
                self.assertIsInstance(
                    channel,
                    ast.Name,
                    "the channel id handed to the shared codec is computed "
                    "rather than named, so no reader can tell which channel "
                    "this composes for: %s" % ast.dump(node),
                )
                seen[holder.name] = channel.id
        self.assertEqual(
            seen,
            allowed,
            "say_wire.py composes for a channel/function pairing this file "
            "does not allow. The GMGlobal id may be passed ONLY by the gated "
            "say composer; the refusal notice may pass ONLY the LocalTalk "
            "id. Found: %s" % seen,
        )


class TheComposerItselfTests(_Case):
    def test_the_notice_text_is_twelve_ascii_characters(self):
        self.assertEqual(say_wire.SPEED_DENIED_NOTICE_TEXT, "SPEED DENIED")
        self.assertEqual(len(say_wire.SPEED_DENIED_NOTICE_TEXT), 12)
        self.assertEqual(say_wire.NOTICE_TEXT_EXACT_LENGTH, 12)
        self.assertTrue(say_wire.SPEED_DENIED_NOTICE_TEXT.isascii())

    def test_it_composes_local_talk_never_the_gated_gm_global_channel(self):
        self.assertEqual(say_wire.LOCAL_TALK_CHANNEL_ID, 0xAC52)
        self.assertNotEqual(
            say_wire.LOCAL_TALK_CHANNEL_ID, say_wire.GM_GLOBAL_CHANNEL_ID
        )

    def test_the_say_gate_is_untouched_by_this_route(self):
        # The GMGlobal lock (COO-DECISION 20260829_0041) is about a different
        # channel and stays shut; this route must never be read as lifting it.
        self.assertIsNone(say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED)

    def test_a_longer_or_shorter_line_is_refused_not_truncated(self):
        for text in ("", "SHORT", "SPEED DENIED FOR THIS CHARACTER"):
            with self.assertRaises(say_wire.NoticeWireError):
                say_wire.make_local_talk_notice_frame(self.legacy, text)

    def test_a_non_ascii_line_of_the_right_length_is_refused(self):
        with self.assertRaises(say_wire.NoticeWireError):
            say_wire.make_local_talk_notice_frame(self.legacy, "ปฏิเสธความเร็ว")

    def test_a_str_subclass_is_refused_like_every_other_lying_shape(self):
        class Sneaky(str):
            def __len__(self):
                return 12

        with self.assertRaises(say_wire.NoticeWireError):
            say_wire.make_local_talk_notice_frame(
                self.legacy, Sneaky("this is much longer than twelve")
            )

    def test_a_broken_legacy_seam_is_this_modules_error_type_too(self):
        # pf-adversary (round `aa9ajr`, D7): `None` and a bare object both
        # raised `AttributeError` straight through a function that promises
        # one error type, and the next caller writing `except NoticeWireError`
        # would meet it as an unexpected-exception event on the listener
        # thread instead.
        for broken in (None, object()):
            with self.subTest(legacy=type(broken).__name__):
                with self.assertRaises(say_wire.NoticeWireError):
                    say_wire.make_local_talk_notice_frame(
                        broken, say_wire.SPEED_DENIED_NOTICE_TEXT
                    )

    def test_a_speaker_other_than_the_measured_empty_one_is_refused(self):
        # D9: the 12-character body is pinned to the evidence; the speaker is
        # the other half of that same evidence and was type-checked only.
        for speaker in ("G" * 4000, "GM", "\u0e01"):
            with self.subTest(speaker=speaker[:8]):
                with self.assertRaises(say_wire.NoticeWireError):
                    say_wire.make_local_talk_notice_frame(
                        self.legacy,
                        say_wire.SPEED_DENIED_NOTICE_TEXT,
                        speaker=speaker,
                    )

    def test_twelve_control_characters_are_refused(self):
        # D9: `"\x00" * 12` is ASCII and twelve characters long, and nobody
        # has ever watched a control-character line render.
        with self.assertRaises(say_wire.NoticeWireError):
            say_wire.make_local_talk_notice_frame(self.legacy, "\x00" * 12)

    def test_a_codec_failure_surfaces_as_this_modules_error_type(self):
        with mock.patch.object(
            say_wire,
            "make_channel_message_response",
            side_effect=RuntimeError("HYP-PF-019 composed PC size drift"),
        ):
            with self.assertRaises(say_wire.NoticeWireError):
                say_wire.make_local_talk_notice_frame(
                    self.legacy, say_wire.SPEED_DENIED_NOTICE_TEXT
                )

    def test_a_notice_that_cannot_be_composed_leaves_the_refusal_intact(self):
        """Fail-closed, and NAMED: the courtesy may never break the command."""
        session = FakeSession(store=FakeStore(CANONICAL_DB_PATH))
        with mock.patch.object(
            say_wire,
            "make_local_talk_notice_frame",
            side_effect=RuntimeError("boom"),
        ):
            action = self.act(session)
        self.assertIsNone(action)
        self.assertTrue(
            any(
                event.startswith(
                    chat_command_action.EVENT_SPEED_DENIED_NOTICE_FAILED_PREFIX
                )
                for event in session.events
            ),
            session.events,
        )
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB, session.events
        )


if __name__ == "__main__":
    unittest.main()
