"""LANE-GM: the `speed` half of the chat line -> outbound ACTION path.

CORE-REQUEST-GM-049 (`pf_bridge/notes_to_chief/20260901_1728_LANE-GM-CORE-
REQUEST-GM-049-speed-sparse-x7-runtime-send-point.md`), wired behind a
SCOPED, temporary exception to `attr_wire.UPDATE_ATTR_VITAL_VERSION_
CONFIRMED` (`COO-DECISION 2026-09-01T18:47+07:00`, `pf_bridge/notes_to_
chief/20260901_1847_COO-DECISION-gm049-vital-version-gate-scoped-
exception-c.md`).  This file proves the `speed` half, mirroring
`tests/test_gm_say_action.py`'s shape (single-socket send, no DB write, no
move-authority interaction) with the differences that shape actually has:

1. THE GATE DEFAULTS OPEN, UNLIKE `say`'s.  `UPDATE_ATTR_VITAL_VERSION_
   CONFIRMED` is `0` today (the scoped exception), not `None` -- so a test
   that means to exercise the withheld branch must force the gate SHUT
   itself (`close_the_version_gate`), the same discipline
   `test_gm_chat_command_action.py`'s `VersionGateTests` already uses for
   `teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED` since RE-129 shipped.
2. IDENTITY, NOT POSITION.  `_speed_action` reads `identity_lo`/
   `identity_hi` off `session.foundation.selected` -- a field `say` never
   touches and `warp` reads `.position` from instead.  A connection with no
   selected character (or one missing the fields) is a named refusal.
3. THE LABEL MUST NOT SAY TELEPORT, same reason as `say`'s: `runtime.py`'s
   `_move_authority_note_server_moves` reopens the move-authority grace
   window on that exact substring, and `/speed` moves nobody.
"""
from __future__ import annotations

import ast
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

from pirateforce_foundation.gm import attr_wire  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import speed_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"


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
    """Only the three fields `_speed_action` reads off `.selected`.

    ~~"`id`/`position` are deliberately absent -- `speed` reads neither"~~ --
    struck, not deleted: `id` IS read now, since `/speed` writes the row
    before it composes the frame (`_selected_speed_character_id`).
    `.position` stays absent for the original reason: `/speed` moves nobody,
    and a future edit that starts reaching for a position fails here instead
    of quietly working on a real session.
    """

    def __init__(self, identity_lo=1, identity_hi=0, character_id=1):
        self.identity_lo = identity_lo
        self.identity_hi = identity_hi
        self.id = character_id


class FakeStore:
    """`.path` for the run-copy gate, plus LANE-DB's persistence entry point.

    The method's name and signature are copied from the real
    `store.SQLiteStore.write_typed_attributes_and_compose_sparse`
    (`character_id`, `values`) -> the SPARSE `{x: value}` for the columns
    written.  `PersistenceIntegrationTests` at the bottom of this file runs
    the same command against a REAL `SQLiteStore` on a temp file, so this
    double can never be the only thing the wiring is proven against.
    """

    def __init__(self, path):
        self.path = path
        self.calls = []
        # What the store "reads back".  A `float` per column, keyed the way
        # the real one keys its return: by WIRE FIELD INDEX, not column name.
        self.readback = None
        self.raises = None
        #: The row as it stands.  Empty = the column was never written, which
        #: is the one case `_speed_undo` honestly cannot revert.
        self.stored = {}
        self.undo_writes = []

    def read_typed_attributes(self, character_id):
        """What `_speed_undo` reads BEFORE the write, to know what to put
        back.  `stored` starts empty, which is the never-written-before case
        (`speed_walk` NULL) -- an undo that has nothing to restore."""
        return dict(self.stored)

    def write_typed_attributes(self, character_id, values):
        """The plain write `_speed_undo` restores through -- deliberately NOT
        the compose variant, so an undo can never be refused by a wire-side
        gate."""
        self.undo_writes.append((character_id, dict(values)))
        self.stored.update(values)

    def write_typed_attributes_and_compose_sparse(self, character_id, values):
        self.calls.append((character_id, dict(values)))
        if self.raises is not None:
            raise self.raises
        self.stored.update(values)
        if self.readback is not None:
            return dict(self.readback)
        # Keyed through the send site's own constant, never the literal
        # "speed_walk" typed a second time -- pf-adversary (round `hw6dix`,
        # D5) caught this double doing exactly what the test two hundred
        # lines below forbids.
        return {
            speed_wire.SPEED_FIELD_X: float(
                values[chat_command_action.SPEED_TYPED_COLUMN]
            )
        }


class FakeLifecycle:
    def __init__(self, path):
        self.store = FakeStore(path)


# The default run-copy-style path every test below gets unless it asks for
# something else -- deliberately NOT the canonical filename, so the whole
# suite exercises `_speed_action` past the run-copy-DB gate by default the
# same way it already defaults past the identity read and version gate.
# Mirrors `pf_bridge/GAME_TEST_QUEUE.md`'s GT-193 run-copy naming: a
# timestamped filename, never the bare canonical one.
DEFAULT_RUN_COPY_DB_PATH = "state/pirateforce_gt193_20260901_1200.sqlite3"


class FakeFoundation:
    def __init__(self, selected=None, db_path=DEFAULT_RUN_COPY_DB_PATH):
        self.selected = selected
        # `None` means "no `.lifecycle` at all" -- the same shape
        # `_speed_db_filename` must treat as unreadable, not as canonical
        # for the wrong reason and not as safe.
        self.lifecycle = None if db_path is None else FakeLifecycle(db_path)


_DEFAULT = object()


class FakeSession:
    def __init__(self, token="GM_ONE", selected=_DEFAULT, db_path=_DEFAULT):
        self.token = token
        self.events = []
        if selected is _DEFAULT:
            selected = FakeSelected()
        if db_path is _DEFAULT:
            db_path = DEFAULT_RUN_COPY_DB_PATH
        self.foundation = FakeFoundation(selected, db_path)


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
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

        # GT-193's shape hold (`speed_wire.SPARSE_SHAPE_CLEARED_BY_A_REAL_
        # CLIENT`) sits ABOVE every path this file exercises: with it shut --
        # which is the production default, pinned as the default by
        # `tests/test_gm_speed_shape_hold.py` -- `/speed` never reaches the DB
        # write or the composer at all.  These tests are about what happens
        # BELOW that gate, so they open it explicitly.  Opening it here is a
        # TEST-ONLY simulation of a future attended clearance; it is not
        # evidence that any client has ever accepted this frame shape.
        _shape_hold_opened = mock.patch.object(
            speed_wire, "SPARSE_SHAPE_CLEARED_BY_A_REAL_CLIENT", True
        )
        _shape_hold_opened.start()
        self.addCleanup(_shape_hold_opened.stop)

    def act(self, session, text):
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

    def close_the_version_gate(self):
        """Force the scoped exception shut, to walk the withheld branch.

        `UPDATE_ATTR_VITAL_VERSION_CONFIRMED` is `0` by default (the scoped
        exception this round flipped it to) -- a test proving the withheld
        path exists must patch the gate back to `None` itself, the same
        discipline `test_gm_chat_command_action.py::VersionGateTests` uses
        for `teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED` since RE-129
        shipped.
        """
        return mock.patch.object(
            attr_wire, "UPDATE_ATTR_VITAL_VERSION_CONFIRMED", None
        )

    def assertRefusalWentToTheScreen(self, action):
        """A refused `/speed` returns the ON-SCREEN NOTICE, not `None`.

        ~~`assertIsNone(action)`~~ -- struck, not deleted, because what the
        old spelling asserted was TRUE until COO-DECISION 2026-09-02T03:45
        +07:00 (`pf_bridge/notes_to_chief/20260902_0345_COO-DECISION-speed-
        refusal-localtalk-via-say-wire-12-ascii.md`) ordered path 1: a
        refused `/speed` was silent on the client, and GM-B could not close
        because a tester could not tell "refused" from "the command did
        nothing at all".  Chief wired the notice (`_speed_denied` ->
        `say_wire.make_local_talk_notice_frame`, 0xAC52, body `SPEED
        DENIED`, exactly 12 ASCII), so every refusal now answers the
        connection with one sentence.

        WHAT THIS STILL PINS, AND IT IS THE PART THAT MATTERED: no
        `UpdateAttrVital` goes out -- the command did not run.  The label
        check is what keeps that promise, so a refusal that started emitting
        the COMMAND's frame still goes red here.  What each test asserts
        about rows, events and outcome words is untouched by this change.
        The full nine-path proof (bytes decoded, length pinned, console line
        preserved, `queued` never armed) lives in chief's own
        `tests/test_gm_speed_denied_notice.py`.
        """
        self.assertIsNotNone(
            action,
            "a refused /speed reached the client with nothing at all; "
            "COO-DECISION 20260902_0345 requires the SPEED DENIED notice",
        )
        self.assertEqual(
            action[0],
            chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL,
            "a refused /speed returned an action that is not the refusal "
            "notice: %r" % (action[0],),
        )


class SpeedVersionGateTests(_Case):
    def test_the_shipped_constant_is_zero_by_the_scoped_exception(self):
        # See attr_wire.py's own comment on the constant for the full
        # reasoning (COO-DECISION 20260901_1847, a convergence across
        # RE-105/RE-129, not a byte lifted from either).
        self.assertEqual(attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED, 0)

    def test_a_valid_gm_speed_composes_with_the_gate_open_by_default(self):
        # Unlike `say`'s gate (still None today), this one does not need a
        # test to open it -- proving that IS what this test pins.
        session = FakeSession()
        action = self.act(session, "/speed 5.0")
        self.assertIsNotNone(action)

    def test_a_valid_gm_speed_withholds_when_the_gate_is_forced_shut(self):
        session = FakeSession()
        with self.close_the_version_gate():
            action = self.act(session, "/speed 5.0")
        self.assertRefusalWentToTheScreen(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_NO_VERSION, session.events
        )

    def test_the_line_is_still_authorized_and_audited_while_withheld(self):
        session = FakeSession()
        with self.close_the_version_gate():
            self.act(session, "/speed 5.0")
        records = self.log_records()
        # Issued row + the outcome row that names the shut gate
        # (CORE-REQUEST-GM-032).
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["command"], "speed")
        self.assertFalse(records[0]["executed"])
        self.assertEqual(
            records[1]["outcome"],
            chat_command_action.OUTCOME_SPEED_WITHHELD_NO_VERSION,
        )
        self.assertIn(
            f"{chat_command_action.EVENT_ACCEPTED_PREFIX}speed", session.events
        )


class SpeedActionTests(_Case):
    def test_a_speed_command_becomes_a_real_update_attr_vital_action(self):
        session = FakeSession()
        action = self.act(session, "/speed 5.0")
        self.assertIsNotNone(action)
        label, pc, frame, delay = action
        self.assertEqual(label, chat_command_action.SPEED_ACTION_LABEL)
        self.assertEqual(delay, 0.0)
        self.assertIsInstance(pc, (bytes, bytearray))
        self.assertIsInstance(frame, (bytes, bytearray))

    def test_the_bytes_are_the_imported_composers_bytes_not_new_ones(self):
        # This module must never become a second place that knows how to
        # build an UpdateAttrVital frame.
        session = FakeSession(selected=FakeSelected(identity_lo=7, identity_hi=3))
        _label, pc, frame, _delay = self.act(session, "/speed 12.5")
        expected_pc, expected_frame = speed_wire.compose_sparse_speed_update(
            self.legacy, 7, 3, 12.5
        )
        self.assertEqual(bytes(pc), bytes(expected_pc))
        self.assertEqual(bytes(frame), bytes(expected_frame))

    def test_the_identity_reaches_the_frame_from_the_selected_character(self):
        session = FakeSession(
            selected=FakeSelected(identity_lo=0xAABBCCDD, identity_hi=0x11223344)
        )
        _label, _pc, frame, _delay = self.act(session, "/speed 1.0")
        self.assertIn(
            struct.pack("<II", 0xAABBCCDD, 0x11223344), bytes(frame)
        )

    # ~~`test_a_composer_rejection_surfaces_as_a_named_speed_refusal`~~ and
    # ~~`test_the_refusal_outcome_names_the_command_and_the_exception_type`~~
    # -- struck, not deleted.  Both used to prove that a composer failure
    # wrote `refused_speed_<ExcType>`.  Since the persistence half landed,
    # the composer runs AFTER the row is committed, so those two tests were
    # silently exercising write-then-refuse while still asserting the
    # pre-write word and nothing at all about the row (pf-adversary round
    # `hw6dix`, D2 side effect).  Replaced by the two below, which assert the
    # word that now belongs to that branch AND the durable state it leaves.

    def test_a_post_commit_composer_failure_has_its_own_refusal_word(self):
        session = FakeSession()
        with mock.patch.object(
            speed_wire,
            "compose_sparse_speed_update",
            side_effect=speed_wire.SpeedWireError("nope"),
        ):
            action = self.act(session, "/speed 5.0")
        self.assertRefusalWentToTheScreen(action)
        self.assertIn(
            f"{chat_command_action.EVENT_SPEED_PERSIST_COMPOSE_REFUSED_PREFIX}"
            "SpeedWireError",
            session.events,
        )
        # The word must NOT be the pre-write one: that one means the opposite
        # durable state (nothing stored).
        self.assertNotIn(
            f"{chat_command_action.EVENT_SPEED_REFUSED_PREFIX}SpeedWireError",
            session.events,
        )

    def test_that_refusal_says_the_row_is_committed_and_names_the_type(self):
        session = FakeSession()
        with mock.patch.object(
            speed_wire,
            "compose_sparse_speed_update",
            side_effect=speed_wire.SpeedWireError("nope"),
        ):
            self.act(session, "/speed 5.0")
        self.assertEqual(
            self.log_records()[-1]["outcome"],
            "refused_speed_persist_compose_SpeedWireError",
        )
        # The row really is committed on that branch -- which is why it may
        # not share a word with the pre-write refusal.
        self.assertEqual(
            session.foundation.lifecycle.store.calls,
            [(1, {chat_command_action.SPEED_TYPED_COLUMN: 5.0})],
        )

    def test_a_pre_write_parse_refusal_still_uses_the_pre_write_word(self):
        """The other half of the same distinction: nothing stored, old word.

        `parse_speed_value` has to be patched to reach this branch at all --
        `commands.parse_gm_command` applies the identical finite-number check
        at GRAMMAR time, so `/speed fast` is refused before `_speed_action`
        runs (`refused_command_parse_error_GmCommandParseError`).  That is
        why this test patches rather than typing a bad value: the branch is
        the "regardless of source" backstop `speed_wire` documents, and it
        must keep the pre-write word.
        """
        session = FakeSession()
        with mock.patch.object(
            speed_wire,
            "parse_speed_value",
            side_effect=speed_wire.SpeedWireError("nope"),
        ):
            self.assertRefusalWentToTheScreen(self.act(session, "/speed 5.0"))
        self.assertEqual(session.foundation.lifecycle.store.calls, [])
        self.assertIn(
            f"{chat_command_action.EVENT_SPEED_REFUSED_PREFIX}SpeedWireError",
            session.events,
        )
        self.assertEqual(
            self.log_records()[-1]["outcome"], "refused_speed_SpeedWireError"
        )


class SpeedIdentityTests(_Case):
    def test_no_selected_character_is_a_named_refusal_not_a_crash(self):
        session = FakeSession(selected=None)
        action = self.act(session, "/speed 5.0")
        self.assertRefusalWentToTheScreen(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_NO_SELECTED_CHARACTER,
            session.events,
        )

    def test_a_selected_character_missing_identity_is_the_same_named_refusal(self):
        class BareSelected:
            pass

        session = FakeSession(selected=BareSelected())
        action = self.act(session, "/speed 5.0")
        self.assertRefusalWentToTheScreen(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_NO_SELECTED_CHARACTER,
            session.events,
        )

    def test_the_outcome_row_names_the_missing_character_case(self):
        session = FakeSession(selected=None)
        self.act(session, "/speed 5.0")
        records = self.log_records()
        self.assertEqual(
            records[-1]["outcome"],
            chat_command_action.OUTCOME_SPEED_NO_SELECTED_CHARACTER,
        )


class SpeedRunCopyDbGateTests(_Case):
    """CORE-REQUEST-GM-049's run-copy-DB requirement, enforced this round.

    pf-adversary found that the prior docstring's "no existing code-level
    mechanism" claim was false and the gap it excused was live-reachable:
    `session.foundation.lifecycle.store.path` was already the live DB path
    string this process booted against.  This class proves the filename
    heuristic `_speed_db_is_canonical` reads off it -- see that function's
    own docstring, and `_speed_action`'s, for the honest statement of what a
    FILENAME HEURISTIC does and does not guarantee.
    """

    def test_the_canonical_filename_exact_match_withholds(self):
        session = FakeSession(db_path="state/pirateforce.sqlite3")
        action = self.act(session, "/speed 5.0")
        self.assertRefusalWentToTheScreen(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )

    def test_the_bare_canonical_filename_with_no_directory_also_withholds(self):
        session = FakeSession(db_path="pirateforce.sqlite3")
        action = self.act(session, "/speed 5.0")
        self.assertRefusalWentToTheScreen(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )

    def test_an_explicit_run_copy_filename_proceeds_past_this_gate(self):
        # A GT-193-style timestamped filename is exactly what a run-copy
        # boot passes to --db -- this must NOT be refused by this gate.
        session = FakeSession(
            db_path="state/pirateforce_gt193_20260901.sqlite3"
        )
        action = self.act(session, "/speed 5.0")
        self.assertIsNotNone(action)
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )

    def test_a_windows_backslash_path_to_the_canonical_file_is_still_caught(self):
        # `os.path.basename` alone would leave this whole string uncut on a
        # Linux process -- this is what proves the explicit `/`-and-`\`
        # split actually does its job rather than trusting the platform's
        # own separator.
        session = FakeSession(db_path="state\\pirateforce.sqlite3")
        action = self.act(session, "/speed 5.0")
        self.assertRefusalWentToTheScreen(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )

    def test_every_windows_alias_of_the_canonical_name_still_withholds(self):
        """pf-adversary (round `hw6dix`, D3): the exact `==` this gate used
        authorized a WRITE to the canonical file through all of these.

        `app.py:660` keeps the operator's `--db` string verbatim -- no
        `resolve()`, no normalization -- so every spelling below is what a
        real boot can hand this gate, and every one of them opens the SAME
        file on Windows.
        """
        for path in (
            "state/PirateForce.sqlite3",
            "state/PIRATEFORCE.SQLITE3",
            "state\\PirateForce.sqlite3",
            "state/pirateforce.sqlite3 ",
            "state/pirateforce.sqlite3.",
            "state/pirateforce.sqlite3::$DATA",
            "state/PIRATE~1.SQL",
        ):
            with self.subTest(db_path=path):
                session = FakeSession(db_path=path)
                self.assertRefusalWentToTheScreen(self.act(session, "/speed 5.0"))
                self.assertIn(
                    chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
                    session.events,
                )

    def test_a_hard_link_to_the_canonical_file_withholds(self):
        """The one check that sees past strings entirely.

        A short name, a case variant, a hard link or a junction all defeat a
        filename comparison; `os.path.samefile` against a sibling
        `pirateforce.sqlite3` does not.  Built here as a hard link because
        that is the alias a POSIX runner can actually create -- the property
        under test (two names, one file) is the same one an 8.3 alias has.
        """
        canonical = self.tmp / chat_command_action.CANONICAL_DB_FILENAME
        canonical.write_bytes(b"")
        alias = self.tmp / "pirateforce_gt193_looks_like_a_run_copy.sqlite3"
        os.link(canonical, alias)
        session = FakeSession(db_path=str(alias))
        self.assertRefusalWentToTheScreen(self.act(session, "/speed 5.0"))
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )

    def test_a_real_separate_run_copy_beside_the_canonical_file_proceeds(self):
        # The control for the test above: a genuinely different file in the
        # same directory as the canonical one must NOT be refused, or a
        # standard `staged/*_boot.ps1` run-copy could never send.
        canonical = self.tmp / chat_command_action.CANONICAL_DB_FILENAME
        canonical.write_bytes(b"")
        run_copy = self.tmp / "pirateforce_gt193_20260902_0129.sqlite3"
        run_copy.write_bytes(b"")
        session = FakeSession(db_path=str(run_copy))
        self.assertIsNotNone(self.act(session, "/speed 5.0"))
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )

    def test_an_unreadable_path_withholds_rather_than_proceeding(self):
        # `db_path=None` means `FakeFoundation` carries no `.lifecycle` at
        # all -- a test double / unusual session shape this function cannot
        # read.  "Cannot prove this is safe" must refuse, never proceed as
        # if it were proven safe.
        session = FakeSession(db_path=None)
        action = self.act(session, "/speed 5.0")
        self.assertRefusalWentToTheScreen(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )

    def test_this_gate_runs_before_the_identity_read(self):
        # Point 4 of the fix: a wrong-DB refusal must not depend on a
        # character having been selected first.  No character is selected
        # here, and the refusal must still be the DB one, not the identity
        # one.
        session = FakeSession(selected=None, db_path="state/pirateforce.sqlite3")
        action = self.act(session, "/speed 5.0")
        self.assertRefusalWentToTheScreen(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_NO_SELECTED_CHARACTER,
            session.events,
        )

    def test_the_outcome_row_names_the_canonical_db_case(self):
        session = FakeSession(db_path="state/pirateforce.sqlite3")
        self.act(session, "/speed 5.0")
        records = self.log_records()
        self.assertEqual(
            records[-1]["outcome"],
            chat_command_action.OUTCOME_SPEED_WITHHELD_CANONICAL_DB,
        )

    def test_the_path_string_itself_never_reaches_an_event_name(self):
        # Defense in depth, same rule this whole module states for every
        # other refusal: the event/outcome names are fixed literals, never
        # built from anything read off the session, so a run-copy filename
        # cannot leak through this gate's refusal either.
        session = FakeSession(
            db_path="state/pirateforce_SECRET_TOKEN_1234.sqlite3"
        )
        self.act(session, "/speed 5.0")
        self.assertFalse(
            any("SECRET_TOKEN" in event for event in session.events),
            session.events,
        )


class SpeedLabelTests(_Case):
    """The label is not decoration; runtime.py reads it."""

    def test_the_speed_label_does_not_contain_teleport(self):
        self.assertNotIn("TELEPORT", chat_command_action.SPEED_ACTION_LABEL)

    def test_the_label_is_ascii(self):
        chat_command_action.SPEED_ACTION_LABEL.encode("ascii")

    def test_the_speed_label_is_distinct_from_the_others(self):
        self.assertNotEqual(
            chat_command_action.SPEED_ACTION_LABEL,
            chat_command_action.SAY_ACTION_LABEL,
        )
        self.assertNotEqual(
            chat_command_action.SPEED_ACTION_LABEL,
            chat_command_action.WARP_ACTION_LABEL,
        )
        self.assertNotEqual(
            chat_command_action.SPEED_ACTION_LABEL,
            chat_command_action.GMPROBE_ACTION_LABEL,
        )


class SpeedPermissionTests(_Case):
    def test_a_non_gm_typing_the_same_line_gets_nothing(self):
        session = FakeSession(token=self.PLAYER_ACCOUNT)
        action = self.act(session, "/speed 5.0")
        self.assertIsNone(action)
        self.assertEqual(self.log_records(), [])
        self.assertFalse(
            any(
                event.startswith(chat_command_action.EVENT_ACCEPTED_PREFIX)
                for event in session.events
            ),
            session.events,
        )


class SpeedCoverageHonestyTests(_Case):
    """The "not wired yet" list has to shrink when a wire is built."""

    def test_speed_is_no_longer_reported_as_having_no_wire_path(self):
        session = FakeSession()
        self.act(session, "/speed 5.0")
        self.assertNotIn(
            f"{chat_command_action.EVENT_NO_WIRE_PATH_PREFIX}speed",
            session.events,
        )




class _StoreWithoutThePersistenceMethod:
    """A store-shaped object carrying only `.path`.

    Exactly what every session double in this file looked like BEFORE the
    persistence half existed -- kept as a named double so the "an old-shaped
    session refuses instead of silently sending an unpersisted frame" branch
    has something real to walk.
    """

    def __init__(self, path):
        self.path = path


class SpeedPersistenceTests(_Case):
    """DB FIRST, WIRE SECOND -- the half added the round LANE-DB's entry
    point (`store.write_typed_attributes_and_compose_sparse`) was live on
    `main`.

    WHAT THIS CLASS DOES AND DOES NOT CLAIM, stated before the first
    assertion rather than left for a reader to infer:

    * it proves the ORDER (no frame composed before the row is written --
      and that one has a live control, see
      `test_no_frame_is_composed_before_the_row_is_written`) and the
      NO-FRAME-ON-REFUSAL rule against a fake store, and the round trip
      against a real `SQLiteStore` on a temp file (`PersistenceIntegration
      Tests`);

    * WHICH OF THESE REFUSALS A REAL BOOT CAN ACTUALLY REACH, because an
      earlier draft of this docstring implied all of them and pf-adversary
      (round `hw6dix`, D6) measured that three cannot:
        - `persist_refused_TypedAttrError` -- REACHABLE, and
          `PersistenceIntegrationTests` reaches it with `1e40`;
        - `no_store` -- `SQLiteStore` always defines the method;
        - `no_character_id` -- `SQLiteStore._character` always builds
          `Character(int(r['id']), ...)`, a positive int;
        - `persist_readback_unusable` -- every value comes back through
          `persistence_typed_attrs.validate`, which returns `int | float`.
      The last three are defence against session shapes production does not
      currently produce (test doubles, replay tools, a future caller), and
      they are kept for that reason -- not because a boot can hit them
      today.  Saying so here is the point: a green test on an unreachable
      branch is not evidence about a real boot;
    * it does NOT prove the client accepts or applies the frame, and it does
      NOT prove `/speed` is "done".  That is `GT-193`'s job, attended, and
      only its condition (b) is what this wiring moves;
    * the DB-first ORDERING ITSELF is `[ASSUMPTION OF LANE-GM, AWAITING
      COO]` (`pf_bridge/notes_to_chief/20260902_0017_LANE-GM-ASK-COO-speed-
      db-first-ordering-change.md`).  If COO rules wire-first, these tests
      are what has to change, and they are written to fail loudly rather
      than to bend.
    """

    def store_of(self, session):
        return session.foundation.lifecycle.store

    def test_the_store_is_called_with_this_connections_row_and_value(self):
        session = FakeSession(selected=FakeSelected(character_id=42))
        action = self.act(session, "/speed 5.0")
        self.assertIsNotNone(action)
        self.assertEqual(
            self.store_of(session).calls,
            [(42, {chat_command_action.SPEED_TYPED_COLUMN: 5.0})],
        )

    def test_no_frame_is_composed_before_the_row_is_written(self):
        """The ORDER, with a control that can actually see it.

        pf-adversary (round `hw6dix`, D4) inserted a full
        `compose_sparse_speed_update` call ABOVE the write -- so a frame
        demonstrably existed before the row -- and every test in this file
        stayed green, because asserting "the store was called with these
        args" says nothing about when.  This wraps the composer and records
        how many rows the store had written each time it ran: a compose
        before the write shows up as a `0` in that list.
        """
        session = FakeSession()
        store = self.store_of(session)
        rows_written_at_each_compose = []
        real = speed_wire.compose_sparse_speed_update

        def recording(*args, **kwargs):
            rows_written_at_each_compose.append(len(store.calls))
            return real(*args, **kwargs)

        with mock.patch.object(
            speed_wire, "compose_sparse_speed_update", recording
        ):
            self.assertIsNotNone(self.act(session, "/speed 5.0"))
        self.assertEqual(rows_written_at_each_compose, [1])

    def test_the_send_sites_column_constant_resolves_to_lane_dbs_column(self):
        self.assertEqual(
            chat_command_action.SPEED_TYPED_COLUMN,
            persistence_typed_attrs.column_for(speed_wire.SPEED_FIELD_X),
        )

    def test_that_constant_is_DERIVED_from_the_table_not_a_string_literal(self):
        """An AST guard, because a value check cannot see the difference.

        pf-adversary (round `hw6dix`, D5) mutated `SPEED_TYPED_COLUMN` to a
        hardcoded `"speed_walk"` and every test stayed green -- including a
        first attempt at a fix that compared the constant against
        `column_for(7)`, which of course AGREES today.  The property the
        constant's own comment claims ("resolved THROUGH their own table ...
        a schema change becomes a loud failure, not a silent refusal") is
        about the SHAPE of the assignment, so that is what this reads.  Same
        technique `tests/test_persistence_attr_compose.py` uses on its own
        producers.
        """
        source = (
            ROOT / "src/pirateforce_foundation/gm/chat_command_action.py"
        ).read_text(encoding="utf-8")
        assignments = [
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "SPEED_TYPED_COLUMN"
                for target in node.targets
            )
        ]
        self.assertEqual(len(assignments), 1, "expected exactly one binding")
        value = assignments[0].value
        self.assertIsInstance(
            value,
            ast.Call,
            "SPEED_TYPED_COLUMN must be CALLED out of the typed-attribute "
            "table, never spelled as a literal",
        )
        self.assertEqual(
            getattr(value.func, "attr", getattr(value.func, "id", None)),
            "column_for",
        )

    def test_the_column_written_is_the_one_the_typed_table_owns_for_x7(self):
        session = FakeSession()
        self.act(session, "/speed 3.0")
        (_character_id, values), = self.store_of(session).calls
        self.assertEqual(
            list(values),
            [persistence_typed_attrs.column_for(speed_wire.SPEED_FIELD_X)],
        )

    def test_exactly_one_field_is_written_never_a_merged_block(self):
        # COO-ORDER 20260901_1641's rule for this path, now applying to the
        # WRITE as well as to the frame.
        session = FakeSession()
        self.act(session, "/speed 3.0")
        (_character_id, values), = self.store_of(session).calls
        self.assertEqual(len(values), 1)

    def test_the_frame_carries_the_stores_readback_not_the_typed_text(self):
        # The store says the row holds 9.5 while the GM typed 5.0.  Real
        # stores round f32 on the way in; this double exaggerates the same
        # divergence so the assertion can see which number won.
        session = FakeSession(selected=FakeSelected(identity_lo=7, identity_hi=3))
        self.store_of(session).readback = {speed_wire.SPEED_FIELD_X: 9.5}
        _label, pc, frame, _delay = self.act(session, "/speed 5.0")
        expected_pc, expected_frame = speed_wire.compose_sparse_speed_update(
            self.legacy, 7, 3, 9.5
        )
        self.assertEqual(bytes(pc), bytes(expected_pc))
        self.assertEqual(bytes(frame), bytes(expected_frame))
        typed_text_frame = speed_wire.compose_sparse_speed_update(
            self.legacy, 7, 3, 5.0
        )[1]
        self.assertNotEqual(bytes(frame), bytes(typed_text_frame))

    def test_a_store_refusal_sends_no_frame_and_names_only_the_type(self):
        session = FakeSession()
        self.store_of(session).raises = KeyError(1)
        action = self.act(session, "/speed 5.0")
        self.assertRefusalWentToTheScreen(action)
        self.assertIn(
            f"{chat_command_action.EVENT_SPEED_PERSIST_REFUSED_PREFIX}KeyError",
            session.events,
        )
        self.assertEqual(
            self.log_records()[-1]["outcome"],
            f"{chat_command_action.OUTCOME_SPEED_PERSIST_REFUSED_PREFIX}KeyError",
        )

    def test_a_store_refusal_message_never_reaches_the_audit_row(self):
        # The same TYPE-name-only discipline every other refusal in this
        # module keeps: an exception message can embed the GM's typed text.
        session = FakeSession()
        self.store_of(session).raises = ValueError("/speed 999999 by GM_ONE")
        self.act(session, "/speed 999999")
        row = self.log_records()[-1]["outcome"]
        self.assertNotIn("999999", row)
        self.assertNotIn("GM_ONE", row)

    def test_an_unusable_readback_sends_no_frame(self):
        session = FakeSession()
        self.store_of(session).readback = {speed_wire.SPEED_FIELD_X: "fast"}
        action = self.act(session, "/speed 5.0")
        self.assertRefusalWentToTheScreen(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_PERSIST_READBACK_UNUSABLE,
            session.events,
        )

    def test_a_readback_missing_the_field_entirely_sends_no_frame(self):
        session = FakeSession()
        self.store_of(session).readback = {}
        self.assertRefusalWentToTheScreen(self.act(session, "/speed 5.0"))

    def test_a_boolean_readback_is_refused_rather_than_encoded_as_one(self):
        # `True` is an `int` in python and would ride the wire as `1.0`.
        session = FakeSession()
        self.store_of(session).readback = {speed_wire.SPEED_FIELD_X: True}
        self.assertRefusalWentToTheScreen(self.act(session, "/speed 5.0"))
        self.assertIn(
            chat_command_action.EVENT_SPEED_PERSIST_READBACK_UNUSABLE,
            session.events,
        )

    def test_a_store_with_no_persistence_method_refuses(self):
        session = FakeSession()
        session.foundation.lifecycle.store = _StoreWithoutThePersistenceMethod(
            DEFAULT_RUN_COPY_DB_PATH
        )
        action = self.act(session, "/speed 5.0")
        self.assertRefusalWentToTheScreen(action)
        self.assertIn(chat_command_action.EVENT_SPEED_NO_STORE, session.events)

    def test_a_selected_character_with_no_id_refuses_before_writing(self):
        session = FakeSession(selected=FakeSelected())
        del session.foundation.selected.id
        action = self.act(session, "/speed 5.0")
        self.assertRefusalWentToTheScreen(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_NO_CHARACTER_ID, session.events
        )
        self.assertEqual(self.store_of(session).calls, [])

    def test_a_non_positive_id_is_refused_rather_than_written_against(self):
        # A rowid is >= 1; `0` is a sentinel that leaked, and handing it to a
        # keyed write would read as a lookup miss instead of a read fault.
        for bad in (0, -1, True, "3"):
            with self.subTest(character_id=bad):
                session = FakeSession(selected=FakeSelected(character_id=bad))
                self.assertRefusalWentToTheScreen(self.act(session, "/speed 5.0"))
                self.assertEqual(self.store_of(session).calls, [])

    def test_the_canonical_db_gate_fires_before_any_write(self):
        # The gate was a send gate; it is now also the only thing standing
        # between this lane and writing the canonical database.
        session = FakeSession(db_path="state/pirateforce.sqlite3")
        self.assertRefusalWentToTheScreen(self.act(session, "/speed 5.0"))
        self.assertEqual(self.store_of(session).calls, [])

    def test_a_shut_version_gate_writes_nothing_either(self):
        # Withheld means withheld: no frame AND no row.  A round that moved
        # the write above the version gate would leave a database holding a
        # speed no client was ever told about.
        session = FakeSession()
        with self.close_the_version_gate():
            self.assertRefusalWentToTheScreen(self.act(session, "/speed 5.0"))
        self.assertEqual(self.store_of(session).calls, [])

    def test_an_unparseable_value_writes_nothing(self):
        session = FakeSession()
        action = self.act(session, "/speed fast")
        # NOT `assertIsNone` since COO-DECISION `0647`: `/speed fast` is
        # refused by the GRAMMAR, and that layer now answers with the
        # `TYPO REFUSED` notice.  The claim in the test's NAME -- that
        # nothing is written -- is the line below, and it is unchanged.
        self.assertEqual(
            action[0], chat_command_action.TYPO_REFUSED_NOTICE_ACTION_LABEL
        )
        self.assertEqual(self.store_of(session).calls, [])


def _build_wire(selector):
    return b"wire", b"avatar", 0x20000001 + selector, 0


class PersistenceIntegrationTests(_Case):
    """The same command against a REAL `SQLiteStore` on a real temp file.

    The fake store above can only prove this lane calls the method it says
    it calls.  This class is the half that proves the value is still there
    after the write -- read back through a SECOND `SQLiteStore` opened on
    the same file, which is the closest a headless test gets to "the GM
    logs in again tomorrow".

    It is still not `GT-193`: nothing here has a client in it.
    """

    def setUp(self):
        super().setUp()
        # Registered AFTER `_Case.setUp` queued the temp directory's own
        # cleanup, so LIFO runs this one FIRST -- checking after the
        # directory is gone would check nothing.  This guard exists because
        # a leaked sqlite handle is what killed PR #495 on the Windows gate
        # (`TemporaryDirectory.cleanup` -> `WinError 32`), a failure Linux
        # never shows.  `SQLiteStore.connect` closes in a `finally`, so this
        # is a regression guard, not a known leak.
        self.addCleanup(self._assert_no_sqlite_handle_survives)
        self.db_path = self.tmp / "pirateforce_gt193_speedtest.sqlite3"
        self.store = SQLiteStore(self.db_path, MIGRATIONS)
        self.store.migrate()
        account_id = self.store.ensure_account("GM_ONE")
        self.character = self.store.create_character(
            account_id, "SpeedGM", "speedgm", "fingerprint-speed-gm",
            _build_wire, Position(1, 0, 1.0, 2.0, 3.0, heading=0.0),
        )
        self.session = FakeSession(
            selected=FakeSelected(
                identity_lo=self.character.identity_lo,
                identity_hi=self.character.identity_hi,
                character_id=self.character.id,
            )
        )
        self.session.foundation.lifecycle.store = self.store

    def _assert_no_sqlite_handle_survives(self):
        fd_dir = "/proc/self/fd"
        if not os.path.isdir(fd_dir):  # not Linux: the OS enforces it loudly
            return
        root = os.path.realpath(self.tmp)
        held = []
        for fd in os.listdir(fd_dir):
            try:
                target = os.readlink(os.path.join(fd_dir, fd))
            except OSError:
                continue
            if target.startswith(root + os.sep):
                held.append(target)
        self.assertEqual(
            sorted(held),
            [],
            "a handle on this test's temp directory outlives the test; on "
            "Windows TemporaryDirectory.cleanup raises WinError 32 here and "
            "the gate goes red",
        )

    def reopened_speed_walk(self):
        """`speed_walk` as a freshly opened store sees it on disk."""
        return SQLiteStore(self.db_path, MIGRATIONS).read_typed_attributes(
            self.character.id
        ).get("speed_walk")

    def test_the_value_survives_on_disk_for_a_store_opened_afterwards(self):
        action = self.act(self.session, "/speed 620.0")
        self.assertIsNotNone(action)
        self.assertEqual(self.reopened_speed_walk(), 620.0)

    def test_the_frame_and_the_stored_column_are_the_same_float32(self):
        # A GM who types 400.1 must not get a client showing one number and
        # a column holding another: `validate` rounds to f32 on the way in,
        # and the frame is composed from that rounded read-back.
        _label, _pc, frame, _delay = self.act(self.session, "/speed 400.1")
        stored = self.reopened_speed_walk()
        self.assertNotEqual(stored, 400.1)  # rounded, as the column requires
        _expected_pc, expected_frame = speed_wire.compose_sparse_speed_update(
            self.legacy,
            self.character.identity_lo,
            self.character.identity_hi,
            stored,
        )
        self.assertEqual(bytes(frame), bytes(expected_frame))

    def test_a_value_the_column_refuses_leaves_the_row_untouched(self):
        # Out of the wire kind's f32 range -> `TypedAttrError` inside the
        # store, before any UPDATE.  No frame, and nothing on disk.
        self.act(self.session, "/speed 620.0")
        self.assertRefusalWentToTheScreen(self.act(self.session, "/speed 1e40"))
        self.assertEqual(self.reopened_speed_walk(), 620.0)


class SpeedUndoTests(_Case):
    """`/speed` leaves durable state, so it needs a real undo (D1).

    `_make_action`'s own comment states the house rule: "AN EFFECT THAT IS
    ALREADY ON DISK HAS TO COME BACK OFF IT" when the outcome row cannot be
    written.  Before this fix `/speed` was the only handler with durable
    state and no undo, and pf-adversary (round `hw6dix`) measured the result:
    an `OSError` on the outcome append left the column at the new value while
    the console printed "anything it had in hand was dropped with it".
    """

    def break_the_outcome_append(self):
        """Fail the SECOND audit append only -- the `issued` row still lands,
        which is the state that makes the trail broken rather than absent."""
        real = chat_command_action.log_gm_command_outcome

        def failing(*args, **kwargs):
            raise OSError(28, "no space left on device")

        return mock.patch.object(
            chat_command_action, "log_gm_command_outcome", failing
        ), real

    def test_a_failed_outcome_append_puts_the_previous_speed_back(self):
        session = FakeSession()
        store = session.foundation.lifecycle.store
        store.stored = {chat_command_action.SPEED_TYPED_COLUMN: 100.0}
        patcher, _real = self.break_the_outcome_append()
        with patcher:
            action = self.act(session, "/speed 777.0")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_STAGE_REVERTED, session.events
        )
        self.assertEqual(
            store.stored[chat_command_action.SPEED_TYPED_COLUMN], 100.0
        )

    def test_the_restore_goes_through_the_plain_write_not_the_compose_one(self):
        # An undo that could be refused by the wire-side compose gate is not
        # an undo.
        session = FakeSession()
        store = session.foundation.lifecycle.store
        store.stored = {chat_command_action.SPEED_TYPED_COLUMN: 100.0}
        patcher, _real = self.break_the_outcome_append()
        with patcher:
            self.act(session, "/speed 777.0")
        self.assertEqual(
            store.undo_writes,
            [(1, {chat_command_action.SPEED_TYPED_COLUMN: 100.0})],
        )

    def test_a_first_ever_speed_reports_not_reverted_rather_than_lying(self):
        # `write_typed_attributes` refuses `None` outright and this API has no
        # way to clear a column back to NULL, so there is nothing to put back.
        # The honest outcome is `not_reverted`, never a silent success.
        session = FakeSession()
        store = session.foundation.lifecycle.store
        self.assertEqual(store.stored, {})
        patcher, _real = self.break_the_outcome_append()
        with patcher:
            self.act(session, "/speed 777.0")
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_STAGE_NOT_REVERTED,
            session.events,
        )
        self.assertEqual(store.undo_writes, [])

    def test_a_successful_round_never_runs_the_undo(self):
        session = FakeSession()
        store = session.foundation.lifecycle.store
        store.stored = {chat_command_action.SPEED_TYPED_COLUMN: 100.0}
        self.assertIsNotNone(self.act(session, "/speed 777.0"))
        self.assertEqual(store.undo_writes, [])
        self.assertEqual(
            store.stored[chat_command_action.SPEED_TYPED_COLUMN], 777.0
        )

    def test_a_post_commit_compose_failure_also_carries_the_undo(self):
        # That branch commits too, so an audit failure on top of it must be
        # able to take the row back off disk the same way.
        session = FakeSession()
        store = session.foundation.lifecycle.store
        store.stored = {chat_command_action.SPEED_TYPED_COLUMN: 100.0}
        patcher, _real = self.break_the_outcome_append()
        with patcher, mock.patch.object(
            speed_wire,
            "compose_sparse_speed_update",
            side_effect=speed_wire.SpeedWireError("nope"),
        ):
            self.act(session, "/speed 777.0")
        self.assertEqual(
            store.stored[chat_command_action.SPEED_TYPED_COLUMN], 100.0
        )


class UndoIntegrationTests(PersistenceIntegrationTests):
    """The same undo against a REAL `SQLiteStore`, not the double."""

    def test_the_row_on_disk_goes_back_when_the_outcome_row_cannot(self):
        self.act(self.session, "/speed 100.0")
        self.assertEqual(self.reopened_speed_walk(), 100.0)
        with mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            mock.Mock(side_effect=OSError(28, "no space left on device")),
        ):
            action = self.act(self.session, "/speed 777.0")
        self.assertIsNone(action)
        self.assertEqual(self.reopened_speed_walk(), 100.0)



class _StoreThatReturnsNone(FakeStore):
    """LANE-DB's entry point answering `None` instead of a sparse mapping.

    `COO-DECISION 2026-09-02T01:47+07:00` names this case by hand -- "DB
    khuen None" -- as one of the three the wiring must be tested against
    (parse failure / DB returns None / success).  `FakeStore` cannot express
    it: its `readback` attribute is read as "use this mapping instead of the
    default", so setting it to `None` selects the DEFAULT rather than the
    answer under test.  A subclass is the honest way to say it, and it keeps
    the write itself real -- the row IS updated before the `None` comes
    back, which is exactly why the refusal below must not be read as
    "nothing was stored".
    """

    def write_typed_attributes_and_compose_sparse(self, character_id, values):
        self.calls.append((character_id, dict(values)))
        self.stored.update(values)
        return None


class TheRefusalNamesThisConnectionTests(_Case):
    """Every `/speed` refusal writes ONE server line carrying identity.

    THE DECISION THIS FILE PINS.  `COO-DECISION 2026-09-02T01:47+07:00`
    (`pf_bridge/notes_to_chief/20260902_0147_COO-DECISION-speed-db-first-
    then-wire-refusal-must-be-visible.md`) confirmed DB-before-wire and
    attached a condition to it: a refusal may not be SILENT.  It asks for
    two things, and this lane could deliver exactly one of them this round:

      * DELIVERED, and pinned here -- "log fang server one line carrying
        identity and the reason".  The reason half already existed
        (`why=` + `blocked_on=`, round `tvbiqc`); the identity half did not.
        `account=` is NOT identity: `chat_command_action`'s own docstrings
        record that `session.token` is the process-wide `--token`, one
        string shared by every connection, so a line carrying only it cannot
        answer "whose row".
      * NOT DELIVERED -- the chat line the GM reads at the client.  TWO
        server->client text routes exist, not one (pf-adversary D3 corrected
        this class's first draft, which claimed `say_wire` was the only one):
        `0x9F2C` GMGlobal, whose gate `COO-DECISION 2026-08-29T00:41+07:00`
        holds shut on three conditions this round cannot clear, and `0xAC52`
        Channel_LocalTalkMessage, whose echo IS attended-proven to render
        (`docs/FUNCTIONAL_COVERAGE.json`, `chat_input_echo_hypothesis` =
        `runtime_pass`, GT-009) but sits behind a `production_allowed: False`
        scenario, was proven at exactly one message length, and is closed to
        this zone by `test_gm_say_gate_lock.py::NoSecondCompositionRouteTests`
        anyway.  `SayVersionGateTests` and that lock file are what would
        (correctly) go red if this lane flipped either to satisfy the newer
        decision, so it asked instead:
        `pf_bridge/notes_to_chief/20260902_0229_LANE-GM-ASK-COO-speed-
        refusal-on-screen-needs-the-say-gate.md`.

    NONCLAIM: nothing here is client-observable.  Every assertion below
    reads the SERVER HOST'S stderr.  A GM at a real client still sees
    nothing when `/speed` refuses, and this file does not claim otherwise --
    that is precisely the half the letter above is about.
    """

    # A row id and an identity pair no other test in this file uses, so a
    # printer that hardcoded either (or reprinted the account token in their
    # place) cannot pass by coincidence.
    CHARACTER_ID = 4242
    IDENTITY_LO = 0xAABBCCDD
    IDENTITY_HI = 0x11223344

    def selected(self, **kwargs):
        kwargs.setdefault("identity_lo", self.IDENTITY_LO)
        kwargs.setdefault("identity_hi", self.IDENTITY_HI)
        kwargs.setdefault("character_id", self.CHARACTER_ID)
        return FakeSelected(**kwargs)

    def say(self, session, text):
        """One typed line through the real route; returns (action, stderr)."""
        err = io.StringIO()
        out = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            action = self.act(session, text)
        self.assertEqual(out.getvalue(), "", "no GM console line may reach stdout")
        return action, err.getvalue()

    def the_one_line(self, stderr):
        said = [
            line
            for line in stderr.splitlines()
            if line.startswith(chat_command_action.WITHHELD_CONSOLE_TOKEN)
        ]
        self.assertEqual(len(said), 1, stderr)
        return said[0]

    def expected_fields(self):
        return (
            f"character_id={self.CHARACTER_ID}",
            f"identity={self.IDENTITY_LO}:{self.IDENTITY_HI}",
        )

    def test_the_canonical_db_refusal_names_the_connection(self):
        # Reached BEFORE `_speed_action` reads identity for itself -- the
        # gate deliberately runs first so a wrong-DB refusal never depends
        # on a character being selected.  The line still has to carry the
        # identity, which is why the printer reads it rather than being
        # handed whatever the handler happened to have in hand.
        session = FakeSession(
            selected=self.selected(), db_path="state/pirateforce.sqlite3"
        )
        action, err = self.say(session, "/speed 400")
        self.assertRefusalWentToTheScreen(action)
        line = self.the_one_line(err)
        self.assertIn("why=withheld_speed_canonical_db ", line)
        for field in self.expected_fields():
            self.assertIn(field, line)

    def test_a_typo_is_told_apart_by_its_own_token_not_by_an_identity(self):
        """The FIRST of COO's three states, and it does NOT come this way.

        Measured this round, not assumed: `/speed not-a-number`, `/speed
        inf`, `/speed nan` and `/speed 1e400` are all refused by
        `parse_gm_command` UPSTREAM of `_speed_action`, so they print
        `GM_CHAT_COMMAND_REFUSED ... usage='speed <value>'` and never reach
        the no-bytes line at all.  Two consequences, both worth pinning:

          * the tester CAN already separate "typo" from "DB refused" -- the
            two states carry different console tokens, which is a stronger
            separation than two identical tokens with different fields; and
          * `_speed_action`'s own `refused_speed_<ExcType>` branch (the one
            that would carry an identity) is therefore NOT reachable through
            the real route today.  It is defence in depth against a
            hand-built `GmCommand`, the same honesty
            `SpeedCoverageHonestyTests` states for the other unreachable
            refusals in this file -- and the reason the letter to COO says
            the identity half is delivered for the DB states, not for the
            typo state.
        """
        for typed in ("/speed not-a-number", "/speed inf", "/speed 1e400"):
            with self.subTest(typed=typed):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(selected=self.selected())
                action, err = self.say(session, typed)
                # ~~`assertIsNone(action)`~~ -- struck, not deleted, exactly
                # as `assertRefusalWentToTheScreen` records the same move for
                # the DB layer.  It was true until COO-DECISION
                # 2026-09-02T06:47+07:00 (`pf_bridge/notes_to_chief/consumed/
                # 20260902_0647_COO-DECISION-typo-layer-notice-is-TYPO-
                # REFUSED-12-ascii-after-p1.md`) gave the syntax layer its own
                # twelve-character sentence, `TYPO REFUSED`.  What this test
                # was really pinning is untouched and asserted below: no
                # `UpdateAttrVital` goes out, the console tokens still tell
                # the two states apart, and nothing typed is echoed.
                self.assertEqual(
                    action[0],
                    chat_command_action.TYPO_REFUSED_NOTICE_ACTION_LABEL,
                    "a mistyped /speed sent something other than the typo "
                    "notice: %r" % (action[0] if action else None),
                )
                self.assertEqual(
                    [
                        line
                        for line in err.splitlines()
                        if line.startswith(
                            chat_command_action.WITHHELD_CONSOLE_TOKEN
                        )
                    ],
                    [],
                )
                self.assertIn("GM_CHAT_COMMAND_REFUSED", err)
                self.assertIn("usage='speed <value>'", err)
                # The founding rule of every console line in this module.
                self.assertNotIn("not-a-number", err)

    def test_a_shut_version_gate_names_the_connection(self):
        session = FakeSession(selected=self.selected())
        with self.close_the_version_gate():
            action, err = self.say(session, "/speed 400")
        self.assertRefusalWentToTheScreen(action)
        line = self.the_one_line(err)
        self.assertIn("why=withheld_update_attr_vital_version ", line)
        for field in self.expected_fields():
            self.assertIn(field, line)

    def test_a_store_that_refuses_names_the_connection(self):
        session = FakeSession(selected=self.selected())
        session.foundation.lifecycle.store.raises = RuntimeError("column locked")
        action, err = self.say(session, "/speed 400")
        self.assertRefusalWentToTheScreen(action)
        line = self.the_one_line(err)
        self.assertIn("why=refused_speed_persist_RuntimeError", line)
        for field in self.expected_fields():
            self.assertIn(field, line)
        # D2's distinction, re-asserted from the console's chair: the
        # sentence for a post-write refusal must not read as "nothing was
        # stored".
        self.assertIn("do NOT read this as", line)

    def test_a_store_that_answers_none_refuses_and_names_the_connection(self):
        # COO's own third case, spelled by hand in the decision.
        session = FakeSession(selected=self.selected())
        session.foundation.lifecycle.store = _StoreThatReturnsNone(
            DEFAULT_RUN_COPY_DB_PATH
        )
        action, err = self.say(session, "/speed 400")
        self.assertRefusalWentToTheScreen(action)
        line = self.the_one_line(err)
        self.assertIn("why=refused_speed_persist_readback_unusable", line)
        for field in self.expected_fields():
            self.assertIn(field, line)

    def test_a_connection_with_nothing_selected_says_none_not_a_guess(self):
        session = FakeSession(selected=None)
        action, err = self.say(session, "/speed 400")
        self.assertRefusalWentToTheScreen(action)
        line = self.the_one_line(err)
        self.assertIn("character_id=none", line)
        self.assertIn("identity=none", line)
        # `none` is not a gap here -- it is the state the outcome word on the
        # same line is naming.
        self.assertIn("why=refused_speed_no_selected_character ", line)

    def field(self, line, name):
        """The VALUE of one `name=value` field, whitespace-delimited.

        Reading the value rather than substring-matching the whole line is
        what makes the assertions below mutation-proof.  pf-adversary (round
        `c637o1`, D2) defeated the first version of the account test --
        `assertNotIn("identity=GM_ONE")` -- by printing `identity='GM_ONE'`,
        one quote character, and the guard named for that exact mutant went
        green.  An equality check on the extracted value cannot be dressed.
        """
        marker = f" {name}="
        self.assertIn(marker, line)
        return line.split(marker, 1)[1].split(" ", 1)[0]

    def test_the_account_field_is_not_reused_as_the_identity(self):
        # The mutant this test exists for: a printer that satisfies "carries
        # identity" by printing the account token in those fields.  The token
        # is the process-wide `--token`; it answers "which server", never
        # "which row".  Asserted by VALUE EQUALITY, so no amount of quoting,
        # padding or bracketing lets the token through.
        session = FakeSession(
            token=self.GM_ACCOUNT,
            selected=self.selected(),
            db_path="state/pirateforce.sqlite3",
        )
        _, err = self.say(session, "/speed 400")
        line = self.the_one_line(err)
        self.assertIn(f"account='{self.GM_ACCOUNT}'", line)
        self.assertEqual(self.field(line, "character_id"), str(self.CHARACTER_ID))
        self.assertEqual(
            self.field(line, "identity"),
            f"{self.IDENTITY_LO}:{self.IDENTITY_HI}",
        )

    def test_two_rows_in_one_process_get_two_different_lines(self):
        """The mutant that survived 199 of 200 tests until this existed.

        pf-adversary (D2) hardcoded both fields to this class's own
        `4242` / `2864434397:287454020` and to a process-wide stale cache,
        and each mutant killed exactly ONE test -- and only by accident of
        class ordering.  Nothing anywhere asserted that the fields FOLLOW the
        session the printer was handed.

        NONCLAIM, and it is why this test says "rows" and not "connections":
        this does NOT prove the fields identify a connection.  They do not.
        Two connections that selected the same character print identical
        fields, `identity_hi` is `0` for every character this server creates,
        and the server is strictly serial anyway
        (`pf_bridge/FINDINGS_R18_SERVER_IS_STRICTLY_SERIAL.md`).  What is
        proven here is the whole of what the round claims: the line names
        WHICH ROW, and a second row in the same process gets its own answer.
        """
        first = FakeSession(
            selected=self.selected(), db_path="state/pirateforce.sqlite3"
        )
        _, first_err = self.say(first, "/speed 400")
        gm_dispatch.reset_rate_limit_state_for_tests()
        second = FakeSession(
            selected=FakeSelected(
                identity_lo=11, identity_hi=22, character_id=33
            ),
            db_path="state/pirateforce.sqlite3",
        )
        _, second_err = self.say(second, "/speed 400")

        first_line = self.the_one_line(first_err)
        second_line = self.the_one_line(second_err)
        self.assertEqual(
            self.field(first_line, "character_id"), str(self.CHARACTER_ID)
        )
        self.assertEqual(self.field(second_line, "character_id"), "33")
        self.assertEqual(
            self.field(first_line, "identity"),
            f"{self.IDENTITY_LO}:{self.IDENTITY_HI}",
        )
        # Asymmetric on purpose: a printer that swapped lo and hi would read
        # `22:11` here and `11:22` is what the character carries.
        self.assertEqual(self.field(second_line, "identity"), "11:22")

    def test_the_success_path_prints_no_refusal_line_at_all(self):
        # The control.  A line printed on the way OUT would teach an
        # operator to ignore the token, which costs more than it gives.
        session = FakeSession(selected=self.selected())
        action, err = self.say(session, "/speed 400")
        self.assertIsNotNone(action)
        self.assertEqual(
            [
                line
                for line in err.splitlines()
                if line.startswith(chat_command_action.WITHHELD_CONSOLE_TOKEN)
            ],
            [],
        )

    def test_a_character_row_whose_id_is_text_cannot_forge_a_second_line(self):
        """A real forgery attempt, replacing one that attempted none.

        The first version of this test ran a clean `/speed 400` and asserted
        "one line, one token" -- a property that held before this round and
        holds with the feature deleted (pf-adversary D2).  The forgery has to
        come through the only door these fields have: a `.selected` whose
        `id`/`identity_lo` are not the `int`s the read sites demand.  The
        `type(...) is not int` guards in `_selected_speed_character_id` /
        `_selected_speed_identity` are what stop it, so loosening either one
        to a truthiness or `isinstance` check turns this red.
        """
        forged = FakeSelected()
        forged.id = "1\nGM_CHAT_NO_BYTES_SENT account='X' command=speed why=composed"
        forged.identity_lo = "9\nLANE_GM_CHAT_ACTION speed route=action"
        forged.identity_hi = 0
        session = FakeSession(
            selected=forged, db_path="state/pirateforce.sqlite3"
        )
        _, err = self.say(session, "/speed 400")
        line = self.the_one_line(err)
        self.assertEqual(self.field(line, "character_id"), "none")
        self.assertEqual(self.field(line, "identity"), "none")
        self.assertEqual(len(line.splitlines()), 1)
        self.assertEqual(
            err.count(chat_command_action.WITHHELD_CONSOLE_TOKEN), 1, err
        )
        # The route line is legitimately printed for every accepted command
        # and is not a forgery -- what must not happen is a SECOND one.
        self.assertEqual(err.count("LANE_GM_CHAT_ACTION"), 1, err)


class TheLineMustNotLieAboutTheRowItNamesTests(_Case):
    """A line that names a row may not say something false about it.

    pf-adversary (round `c637o1`, D4) measured the harm this round's first
    draft introduced.  A first-ever `/speed` on a character whose
    `speed_walk` was NULL:

      1. commits `400.0`;
      2. loses the audit write (`OSError` on the ndjson);
      3. runs `_speed_undo`, which has nothing to restore, returns False and
         leaves the row AT 400.0 (`gm_chat_action_outcome_stage_not_reverted`
         on `.events`, and nowhere else);
      4. printed `blocked_on='...anything it had in hand was dropped with
         it'` -- next to `character_id=` naming that very row.

    Before this round the operator could not tell WHICH row; with the fields
    added, the line pointed at the row it lied about, which is worse than the
    silence the round set out to fix and is the exact property
    `COO-DECISION 2026-09-02T01:47+07:00` cites.
    """

    def make(self, character_id=4242):
        return FakeSession(
            selected=FakeSelected(
                identity_lo=7, identity_hi=0, character_id=character_id
            )
        )

    def run_with_a_broken_audit(self, session):
        err = io.StringIO()
        with mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            mock.Mock(side_effect=OSError(28, "no space left on device")),
        ), contextlib.redirect_stderr(err):
            action = self.act(session, "/speed 400")
        return action, err.getvalue()

    def the_line(self, stderr):
        said = [
            line
            for line in stderr.splitlines()
            if line.startswith(chat_command_action.WITHHELD_CONSOLE_TOKEN)
        ]
        self.assertEqual(len(said), 1, stderr)
        return said[0]

    def test_an_unrevertable_row_is_reported_as_still_in_place(self):
        session = self.make()
        action, err = self.run_with_a_broken_audit(session)
        self.assertIsNone(action)
        # The row really is still carrying the new value -- that is what
        # makes the old sentence false rather than merely imprecise.
        self.assertEqual(
            session.foundation.lifecycle.store.stored,
            {chat_command_action.SPEED_TYPED_COLUMN: 400.0},
        )
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_STAGE_NOT_REVERTED, session.events
        )
        line = self.the_line(err)
        self.assertIn(
            f"why={chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN_EFFECT_KEPT} ",
            line,
        )
        self.assertIn("STILL IN PLACE", line)
        self.assertIn("character_id=4242", line)
        # The sentence that was false for this state must not be the one
        # printed for it.
        self.assertNotIn("dropped with it", line)

    def test_a_row_that_reverted_keeps_the_original_word(self):
        # The control: when the undo really did put the value back, the
        # older sentence is true and must not be replaced by the new one.
        session = self.make()
        session.foundation.lifecycle.store.stored = {
            chat_command_action.SPEED_TYPED_COLUMN: 100.0
        }
        action, err = self.run_with_a_broken_audit(session)
        self.assertIsNone(action)
        self.assertEqual(
            session.foundation.lifecycle.store.stored,
            {chat_command_action.SPEED_TYPED_COLUMN: 100.0},
        )
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_STAGE_REVERTED, session.events
        )
        line = self.the_line(err)
        self.assertIn(
            f"why={chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN} ", line
        )
        self.assertIn("dropped with it", line)
        self.assertNotIn("STILL IN PLACE", line)

    def test_a_command_with_nothing_to_undo_keeps_the_original_word(self):
        # `/lv` has no durable state at all, so `reverted` is None rather
        # than False and the original word is the honest one.
        session = self.make()
        err = io.StringIO()
        with mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            mock.Mock(side_effect=OSError(28, "no space left on device")),
        ), contextlib.redirect_stderr(err):
            self.act(session, "/lv 10")
        line = self.the_line(err.getvalue())
        self.assertIn(
            f"why={chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN} ", line
        )



# AT THE END OF THE FILE, and it has to stay here.  pf-adversary (round
# `hw6dix`) found this block sitting mid-file, above three of the test
# classes: `python3 tests/test_gm_speed_action.py` then ran 29 of the 59
# tests and printed OK, executing none of that round's work.  The Windows
# gate uses pytest so it was never fooled, but a green that means nothing
# is worse than no green at all.
if __name__ == "__main__":
    unittest.main()
