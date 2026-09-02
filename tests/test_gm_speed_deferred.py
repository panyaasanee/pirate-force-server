"""COO 1847's deferral: `/speed` writes its row and puts NO byte on the wire.

WHAT THIS FILE IS FOR
---------------------
Attended round R303 (2026-09-02, owner at the keyboard) typed `/speed 300` on
a real client.  The frame this lane composed went out, the character showed
HP 0 and money 0 and DIED, and the client then LOCKED ITSELF: 426 inbound
frames afterwards, not one of them a click, the revive buttons never sending a
byte.  The run DB was healthy throughout, so the client reacted to bytes this
lane sent.

COO-DECISION 2026-09-02T18:47+07:00 (`pf_bridge/notes_to_chief/20260902_1847_
COO-DECISION-lane-gm-stop-sending-speed-as-an-attr-frame-now.md`) ruled three
things, and each one is a class below:

  1. `/speed` must not put `LANE_GM_CHAT_SPEED_UPDATE_ATTR_VITAL` on the wire
     again until LANE-DB lands the `speed_walk` login read on `main`;
  2. the route answers with one pure-ASCII console line whose first two words
     are `SPEED DEFERRED`;
  3. "the DB write continues as before -- the DB is already clean; what has to
     stop is the outbound frame, and only that."

WHAT IS PINNED, SAID AS NARROWLY AS IT IS TRUE
----------------------------------------------
PINNED: on the shipped default, a healthy authorized `/speed` returns NO action
at all (this is the "no bytes on this route" test COO's letter asked for); the
row is written first; the console line's prefix is exactly those two words and
its whole line is ASCII; the audit row and the event trail name the deferral by
its own word; and the deferral is fail-closed -- lifting it alone does not send
anything, because the GT-193 shape hold still stands below it.

NOT PINNED, BECAUSE NOBODY MEASURED IT: which byte killed the character.  COO
`1847` forbids guessing it and this lane does not.  The deferral is what a
measured client lockout earns; it is not a diagnosis.

WHAT "NO BYTES" MEANS HERE, EXACTLY.  It means the dispatch returns `None`, so
the serve loop has nothing to send for this command -- not even the LocalTalk
refusal NOTICE that every other `/speed` refusal in this module answers with
(COO-DECISION `0345`).  That reading of COO `1847` (its test requirement is
"pin that no bytes go out on this route") is LANE-GM's, taken because it is the
half that cannot cost an attended round if it is wrong -- the GM loses an
on-screen sentence, the console still says `SPEED DEFERRED`.  It is asked back
in `pf_bridge/notes_to_chief/20260902_2038_LANE-GM-ASK-COO-speed-deferral-
drops-the-on-screen-notice.md` and a COO word reverses it in one branch.
"""
from __future__ import annotations

import io
import json
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import speed_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

RUN_COPY_DB_FILENAME = "pirateforce_lane_gm_20260902_2017.sqlite3"


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
    """Records every write, because "the row still moves" is half of COO 1847."""

    def __init__(self, path):
        self.path = path
        self.calls = []
        self.undo_writes = []
        self.stored = {}

    def read_typed_attributes(self, character_id):
        return dict(self.stored)

    def write_typed_attributes(self, character_id, values):
        # The UNDO's write site, recorded separately from the command's own:
        # "did the row come back off disk?" is a different question from "was
        # it written?", and one list cannot answer both.
        self.undo_writes.append((character_id, dict(values)))
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
    """Runs against the SHIPPED default -- no `setUp` opens anything.

    That is the property this file exists for: every other `/speed` test file
    patches its way past one gate or another, so if a future round flips
    `speed_wire.SPEED_LOGIN_READ_LANDED` without the login read really being on
    `main`, these are the tests that turn red.
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
        # Absolute, inside this test's own temp directory, for the reason the
        # sibling file states: the run-copy gate resolves the store path
        # against the process CWD and fails closed.
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

    def act_capturing_console(self, session, text="/speed 400"):
        """The action AND everything this route printed, as one pair."""
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            action = self.act(session, text)
        return action, buffer.getvalue()

    def _deferred_line(self, console):
        """The one `SPEED DEFERRED` line, or a failure that shows the console.

        Used by every test that reads a FIELD rather than the token: asserting
        against the whole capture would pass on a field that landed on some
        other line, which is the drift `test_the_two_words_are_the_lines_
        PREFIX_not_merely_present` exists to catch on the token itself.
        """
        lines = [
            line
            for line in console.splitlines()
            if line.startswith(chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN)
        ]
        self.assertEqual(len(lines), 1, console)
        return lines[0]

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
        """TEST-ONLY: pretend LANE-DB landed the `speed_walk` login read."""
        return mock.patch.object(speed_wire, "SPEED_LOGIN_READ_LANDED", True)


class TheShippedDefaultDefersTests(_Case):
    def test_the_login_read_is_not_landed_on_main(self):
        self.assertFalse(speed_wire.SPEED_LOGIN_READ_LANDED)

    def test_send_deferred_is_true_on_main(self):
        self.assertTrue(speed_wire.send_deferred())

    def test_the_reader_is_live_not_a_snapshot(self):
        # One line flips it, and every gate re-reads it -- the contract
        # `shape_cleared()` and `shared_vital_version_confirmed()` already keep.
        with self.deferral_lifted():
            self.assertFalse(speed_wire.send_deferred())
        self.assertTrue(speed_wire.send_deferred())


class NoBytesGoOutOnThisRouteTests(_Case):
    """COO 1847's own test requirement, and the reason this file exists."""

    def test_a_healthy_authorized_speed_returns_no_action_at_all(self):
        self.assertIsNone(
            self.act(self.session()),
            "COO 1847 requires /speed to put NO byte on the wire until the "
            "login read lands; an action here is a frame the serve loop sends",
        )

    def test_not_even_the_refusal_notice(self):
        # Narrower than the assertion above and worth its own name: the notice
        # IS bytes, and this route no longer returns one.
        action = self.act(self.session())
        self.assertNotEqual(
            action,
            chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL,
        )
        self.assertIsNone(action)

    def test_the_composer_is_never_reached(self):
        with mock.patch.object(
            speed_wire,
            "compose_sparse_speed_update",
            side_effect=AssertionError("composed while deferred"),
        ):
            self.assertIsNone(self.act(self.session()))

    def test_every_value_a_gm_can_type_is_deferred(self):
        # Including the one that killed the character in R303.
        for text in ("/speed 300", "/speed 400", "/speed 0", "/speed 1e30",
                     "/speed -12.5"):
            with self.subTest(text=text):
                gm_dispatch.reset_rate_limit_state_for_tests()
                self.assertIsNone(self.act(self.session(), text))


class TheRowStillMovesTests(_Case):
    """COO 1847 item 3: the DB write continues, only the frame stops."""

    def test_the_row_is_written(self):
        store = self.store()
        self.act(self.session(store))
        self.assertEqual(len(store.calls), 1)
        self.assertEqual(
            store.stored[chat_command_action.SPEED_TYPED_COLUMN], 400.0
        )

    def test_the_write_names_this_connections_own_character_row(self):
        store = self.store()
        self.act(self.session(store))
        self.assertEqual(store.calls[0][0], FakeSelected().id)

    def test_a_store_refusal_is_still_a_refusal_not_a_deferral(self):
        # The gates ABOVE the deferral keep their own words: a store with no
        # write entry point never reaches COO 1847's line.  A run-copy PATH
        # with no writer, not `store=None`: a session whose path cannot be
        # read at all is refused one gate higher still, by the canonical-DB
        # check, which is its own fail-closed property and not this test's.
        class NoWriter:
            path = self.run_copy_db

        session = FakeSession(NoWriter())
        self.act(session)
        self.assertIn(chat_command_action.EVENT_SPEED_NO_STORE, session.events)
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_DEFERRED, session.events
        )


class TheUndoSurvivesTheDeferralTests(_Case):
    """pf-adversary D6 of round `hj2cry`: nothing pinned this, and it matters.

    The measured mutant: change the deferral's verdict from
    `_Verdict(None, OUTCOME_SPEED_DEFERRED, undo, ...)` to `..., None, ...)`
    and the WHOLE speed suite stayed green -- while an audit-append failure
    then leaves the new value on disk forever, with no outcome row naming it.

    `_make_action`'s house rule is "AN EFFECT THAT IS ALREADY ON DISK HAS TO
    COME BACK OFF IT" when the outcome row cannot be written, and COO `1847`
    made this route the one that always writes.  So the deferral is now the
    handler MOST in need of the undo, not least.
    """

    def break_the_outcome_append(self):
        """Fail the SECOND audit append only -- the `issued` row still lands,
        which is the state that makes the trail broken rather than absent."""

        def failing(*args, **kwargs):
            raise OSError(28, "no space left on device")

        return mock.patch.object(
            chat_command_action, "log_gm_command_outcome", failing
        )

    def test_a_failed_outcome_append_puts_the_previous_speed_back(self):
        store = self.store()
        store.stored = {chat_command_action.SPEED_TYPED_COLUMN: 100.0}
        session = self.session(store)
        with self.break_the_outcome_append():
            self.assertIsNone(self.act(session, "/speed 777.0"))
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_STAGE_REVERTED, session.events
        )
        self.assertEqual(
            store.stored[chat_command_action.SPEED_TYPED_COLUMN], 100.0
        )

    def test_the_restore_goes_through_the_plain_write(self):
        store = self.store()
        store.stored = {chat_command_action.SPEED_TYPED_COLUMN: 100.0}
        with self.break_the_outcome_append():
            self.act(self.session(store), "/speed 777.0")
        self.assertEqual(
            store.undo_writes,
            [(FakeSelected().id, {chat_command_action.SPEED_TYPED_COLUMN: 100.0})],
        )

    def test_a_broken_audit_still_says_so_on_the_console(self):
        # pf-adversary D1: `_announce_console_outcome` used to return on
        # `verdict.line_printed` alone, so `SPEED DEFERRED` printed
        # byte-identical output whether the row was kept, reverted, or stuck.
        # The backstop now speaks BESIDE this line when the audit failed.
        store = self.store()
        store.stored = {chat_command_action.SPEED_TYPED_COLUMN: 100.0}
        buffer = io.StringIO()
        with self.break_the_outcome_append(), redirect_stderr(buffer):
            self.act(self.session(store), "/speed 777.0")
        console = buffer.getvalue()
        self.assertIn(
            chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN, console, console
        )
        self.assertIn(
            chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN, console, console
        )

    def test_an_unrevertable_row_is_reported_as_still_in_place(self):
        # The worst case, and the one the struck code could not print: the
        # column was NULL before, so there is nothing to put back, and the row
        # keeps the new value with no outcome row naming it.
        store = self.store()
        self.assertEqual(store.stored, {})
        buffer = io.StringIO()
        with self.break_the_outcome_append(), redirect_stderr(buffer):
            self.act(self.session(store), "/speed 777.0")
        self.assertIn(
            chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN_EFFECT_KEPT,
            buffer.getvalue(),
            buffer.getvalue(),
        )


class TheWordsAGraderGrepsAreLiteralsTests(_Case):
    """pf-adversary D2: `EVENT_*` names have a literal contract table and
    `OUTCOME_*` values do not, so the exact string a GT grader greps in the
    ndjson could be renamed with every test still green.  These are the
    literals, spelled out, so a rename is a diff a reviewer sees.
    """

    def test_the_audit_word_is_this_exact_string(self):
        self.assertEqual(
            chat_command_action.OUTCOME_SPEED_DEFERRED,
            "withheld_speed_deferred_login_read",
        )

    def test_the_event_name_is_this_exact_string(self):
        self.assertEqual(
            chat_command_action.EVENT_SPEED_DEFERRED,
            "gm_chat_action_speed_deferred_login_read",
        )


class TheLineCarriesTheRowItNamesTests(_Case):
    """COO-DECISION `0147` half (b) requires every /speed refusal to log one
    server line "carrying identity and the reason".

    pf-adversary D2 again: the `SPEED DEFERRED` line now REPLACES the
    `GM_CHAT_NO_BYTES_SENT` line that used to carry those fields on this
    route, and nothing pinned that the replacement still carries them --
    deleting `_identity_fields(...)` or `account=` from it left every test
    green.
    """

    def line(self):
        _action, console = self.act_capturing_console(self.session())
        return next(
            line
            for line in console.splitlines()
            if line.startswith(chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN)
        )

    def test_it_names_the_character_row_the_write_moved(self):
        self.assertIn("character_id=%d" % FakeSelected().id, self.line())

    def test_it_names_the_identity_pair(self):
        selected = FakeSelected()
        self.assertIn(
            "identity=%d:%d" % (selected.identity_lo, selected.identity_hi),
            self.line(),
        )

    def test_it_names_the_account_the_command_was_authorised_under(self):
        self.assertIn("account=", self.line())
        self.assertIn(self.GM_ACCOUNT, self.line())

    def test_it_names_the_audit_word_the_ndjson_will_carry(self):
        self.assertIn(chat_command_action.OUTCOME_SPEED_DEFERRED, self.line())


class TheConsoleSaysSpeedDeferredTests(_Case):
    """COO 1847 item 2: one pure-ASCII line, those two words first."""

    def test_the_token_is_exactly_the_two_words(self):
        self.assertEqual(
            chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN, "SPEED DEFERRED"
        )

    def test_the_line_is_printed_on_the_shipped_route(self):
        _action, console = self.act_capturing_console(self.session())
        self.assertIn(chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN, console)

    def test_the_two_words_are_the_lines_PREFIX_not_merely_present(self):
        # COO's wording is "the prefix must be those two words".  A line that
        # merely contained them somewhere would satisfy a substring test and
        # not the decision.
        _action, console = self.act_capturing_console(self.session())
        lines = [line for line in console.splitlines() if line.strip()]
        deferred = [
            line
            for line in lines
            if chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN in line
        ]
        self.assertEqual(len(deferred), 1, console)
        self.assertTrue(
            deferred[0].startswith(
                chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN
            ),
            deferred[0],
        )

    def test_it_is_the_only_line_this_route_prints_about_the_outcome(self):
        # `_announce_console_outcome` is "the ONE place the console is told",
        # and `line_printed` is how a handler that already spoke stops it from
        # saying the same thing again in a worse vocabulary.  Two lines about
        # one command is how an attended grep starts double-counting.
        _action, console = self.act_capturing_console(self.session())
        self.assertNotIn(
            chat_command_action.WITHHELD_CONSOLE_TOKEN, console, console
        )
        self.assertNotIn(
            chat_command_action.NOTICE_CONSOLE_TOKEN, console, console
        )

    def test_the_line_is_pure_ascii(self):
        # The bridge console is cp874; a non-ASCII byte on this line is a line
        # the operator may not be able to read at all.
        _action, console = self.act_capturing_console(self.session())
        deferred = next(
            line
            for line in console.splitlines()
            if line.startswith(chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN)
        )
        deferred.encode("ascii")  # raises if it is not

    def test_it_never_prints_what_the_gm_TYPED_only_what_the_row_HOLDS(self):
        """~~"the line never prints what the GM typed"~~ -- NARROWED, in the
        round that added `row_written=`, and narrowed deliberately rather than
        deleted, because the old spelling would have banned reporting the
        row at all.

        The property this module actually holds, and the one the threat model
        in `_print_no_bytes_way_out` describes, is that NO CLIENT-CONTROLLED
        TEXT reaches the operator's console: text can carry bidi overrides,
        a line break, a cp874-unencodable byte, or a fake field of its own.
        `row_written=` carries none of that by CONSTRUCTION -- it is
        `repr()` of a Python float that came back out of the store's own
        validator, so its character set is closed over digits, `.`, `e`,
        `+`, `-` whatever was typed.

        For a canonical input the value and the typing coincide, and that is
        not an echo: it is the row agreeing with the request.  The tests
        below prove the difference by measuring a NON-canonical one, where
        the two provably diverge.
        """
        _action, console = self.act_capturing_console(
            self.session(), "/speed 1234.5"
        )
        # The ROW is reported...
        self.assertIn("row_written=1234.5", console)
        # ...and the typed text is still nowhere else on the line: no echo of
        # the raw argument outside the one canonicalised field.
        deferred = self._deferred_line(console)
        self.assertEqual(deferred.count("1234.5"), 2, deferred)
        self.assertIn("next_login_sends=1234.5", deferred)

    def test_the_row_field_is_the_VALUE_not_the_typing(self):
        # The proof that `row_written=` is a canonicalisation and not an
        # echo: three spellings a GM could type for the same number, none of
        # which survives to the console as typed.
        for typed, expected in (
            ("4e2", "400.0"),
            ("400.", "400.0"),
            ("0400.00", "400.0"),
        ):
            with self.subTest(typed=typed):
                _action, console = self.act_capturing_console(
                    self.session(), f"/speed {typed}"
                )
                deferred = self._deferred_line(console)
                field = deferred.split("row_written=", 1)[1].split(" ", 1)[0]
                # Compared as the WHOLE field, not as a substring of the
                # line: `400.` IS a prefix of `400.0`, so a `assertNotIn`
                # here would fail on a canonicalisation that worked.
                self.assertEqual(field, expected)
                self.assertNotEqual(field, typed)

    def test_the_row_field_can_only_ever_hold_number_characters(self):
        # The anti-injection half of the old property, pinned directly on the
        # field instead of inferred from "nothing typed is printed".  A value
        # that reaches this field has been through `float()` and `repr()`, so
        # no typing can put a space, a quote, a `=`, a newline or a non-ASCII
        # byte inside it -- which is what would let a typed argument forge a
        # field of its own on a line an attended grep parses.
        allowed = set("0123456789.e+-")
        for typed in ("1234.5", "4e2", "1e30", "0.0009765625"):
            with self.subTest(typed=typed):
                _action, console = self.act_capturing_console(
                    self.session(), f"/speed {typed}"
                )
                deferred = self._deferred_line(console)
                field = deferred.split("row_written=", 1)[1].split(" ", 1)[0]
                self.assertTrue(field, deferred)
                self.assertLessEqual(set(field), allowed, field)

    def test_the_next_login_fields_come_from_the_login_seam_itself(self):
        """The two `next_login*` fields are not a prediction this lane wrote.

        `login_speed.resolve` IS the function `session.select_and_start` runs
        (`login_speed.resolve_for_character` calls it), and this line calls it
        as a pure predicate on the store's read-back.  `login_speed`'s own
        docstring forbids re-typing its range anywhere else -- "a range typed
        twice is a range that drifts" -- so the pin here is that the console
        agrees with that function, not with a copy of its rules.
        """
        from pirateforce_foundation import login_speed, player_wire

        for typed in ("1234.5", "400"):
            with self.subTest(typed=typed):
                _action, console = self.act_capturing_console(
                    self.session(), f"/speed {typed}"
                )
                deferred = self._deferred_line(console)
                expected = login_speed.resolve(
                    float(typed),
                    fallback=player_wire.PLAYER_LOGIN_MOVEMENT_SPEED,
                )
                self.assertIn(f"next_login={expected.reason}", deferred)
                self.assertIn(
                    f"next_login_sends={float(expected.value)!r}", deferred
                )

    def test_a_row_the_login_would_refuse_says_so_instead_of_the_number(self):
        # The field that makes the line worth reading: a row the login seam
        # will NOT honour is named as such, so a tester who re-logs in and
        # sees the constant is not left thinking the command did nothing.
        # `-1.0` stores and encodes but is not a speed a player can use
        # (`login_speed.ROW_SPEED_NOT_POSITIVE`).
        from pirateforce_foundation import login_speed, player_wire

        _action, console = self.act_capturing_console(
            self.session(), "/speed -1"
        )
        deferred = self._deferred_line(console)
        self.assertIn("row_written=-1.0", deferred)
        self.assertIn(f"next_login={login_speed.ROW_SPEED_NOT_POSITIVE}", deferred)
        self.assertIn(
            "next_login_sends="
            f"{float(player_wire.PLAYER_LOGIN_MOVEMENT_SPEED)!r}",
            deferred,
        )

    def test_a_resolver_that_raises_costs_the_fields_and_not_the_route(self):
        # A DIAGNOSTIC MAY NEVER ALTER DISPATCH, applied to the new fields:
        # the frame is held by `send_deferred()` either way, and a resolver
        # that blows up is NAMED on the line rather than raised at the
        # listener thread.
        session = self.session()
        from pirateforce_foundation import login_speed

        with mock.patch.object(
            login_speed, "resolve", side_effect=RuntimeError("boom")
        ):
            _action, console = self.act_capturing_console(session)
        deferred = self._deferred_line(console)
        self.assertIn(
            f"next_login="
            f"{chat_command_action.SPEED_DEFERRED_NEXT_LOGIN_UNRESOLVED_PREFIX}"
            "RuntimeError",
            deferred,
        )
        self.assertIn(
            f"next_login_sends={chat_command_action.SPEED_DEFERRED_ROW_UNKNOWN}",
            deferred,
        )
        self.assertIn(chat_command_action.EVENT_SPEED_DEFERRED, session.events)

    def test_a_printer_handed_no_read_back_says_not_evaluated(self):
        # The shipped route cannot reach this (the branch runs below
        # `EVENT_SPEED_PERSIST_READBACK_UNUSABLE`), so it gets its own word
        # rather than being spelled like a resolver failure.
        import io
        from contextlib import redirect_stderr

        session = self.session()
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            printed = chat_command_action._print_speed_deferred(
                session, "GM_ONE", "speed"
            )
        self.assertTrue(printed)
        line = buffer.getvalue()
        self.assertIn(
            f"row_written={chat_command_action.SPEED_DEFERRED_ROW_UNKNOWN}", line
        )
        self.assertIn(
            "next_login="
            f"{chat_command_action.SPEED_DEFERRED_NEXT_LOGIN_NOT_EVALUATED}",
            line,
        )

    def test_a_dead_console_costs_the_line_and_nothing_else(self):
        # A DIAGNOSTIC MAY NEVER ALTER DISPATCH: the frame is held by
        # `send_deferred()`, never by whether stderr accepted a line.
        session = self.session()
        with mock.patch.object(sys, "stderr", None):
            self.assertIsNone(self.act(session))
        self.assertIn(chat_command_action.EVENT_SPEED_DEFERRED, session.events)

    def test_a_dead_console_leaves_the_event_trail_and_nothing_else(self):
        """~~"the backstop speaks instead"~~ -- pf-adversary D4 measured that
        it does not, and this test used to claim it did by constructing a
        state production cannot produce (a printer that printed successfully
        and then reported failure).

        Both printers read the same `sys.stderr` through the same helpers, so
        a dead console takes BOTH down.  What survives is `session.events`,
        and that is what an operator with no console has to be told to read.
        """
        session = self.session()
        # NO `redirect_stderr` here, and that is the point: it would REPLACE
        # `sys.stderr` with a live buffer and undo the very condition under
        # test.  A `None` stream has nowhere to write by construction, so the
        # absence of output is not something to assert -- what is assertable
        # is that both printers NAMED the failure instead of swallowing it.
        with mock.patch.object(sys, "stderr", None):
            self.assertIsNone(self.act(session))
        self.assertIn(chat_command_action.EVENT_SPEED_DEFERRED, session.events)
        self.assertTrue(
            any(
                event.startswith(
                    chat_command_action.EVENT_CONSOLE_WRITE_FAILED_PREFIX
                )
                for event in session.events
            ),
            session.events,
        )

    def test_a_raising_stream_costs_the_line_and_not_the_hold(self):
        # The other production shape, and the property that actually matters:
        # the frame is held by `send_deferred()`, never by whether a console
        # accepted a line.
        class Raising:
            def write(self, *_args):
                raise OSError(5, "stream is gone")

            def flush(self):
                pass

        session = self.session()
        with mock.patch.object(sys, "stderr", Raising()):
            self.assertIsNone(self.act(session))
        self.assertIn(chat_command_action.EVENT_SPEED_DEFERRED, session.events)


class TheRecordNamesTheDeferralTests(_Case):
    def test_the_audit_row_carries_its_own_word(self):
        self.act(self.session())
        self.assertIn(
            chat_command_action.OUTCOME_SPEED_DEFERRED, self.audit_outcomes()
        )

    def test_the_audit_word_is_a_withheld_not_a_refused_one(self):
        # The command was fine; this lane did not send it.  An audit reader
        # sorting `refused_*` from `withheld_*` must not find this under the
        # word that means the GM did something wrong.
        self.assertTrue(
            chat_command_action.OUTCOME_SPEED_DEFERRED.startswith(
                chat_command_action.OUTCOME_WITHHELD_PREFIX
            )
        )

    def test_the_session_event_names_it(self):
        session = self.session()
        self.act(session)
        self.assertIn(chat_command_action.EVENT_SPEED_DEFERRED, session.events)

    def test_it_is_not_confused_with_the_shape_hold(self):
        session = self.session()
        self.act(session)
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_WITHHELD_SHAPE_UNCLEARED,
            session.events,
        )

    def test_the_outcome_has_a_console_sentence_for_the_backstop(self):
        self.assertIn(
            chat_command_action.OUTCOME_SPEED_DEFERRED,
            chat_command_action.NO_BYTES_BLOCKERS,
        )

    def test_no_queued_confirmation_is_armed_for_a_command_that_sent_nothing(self):
        # A `queued` row means "this command's frame reached runtime".  It did
        # not.  Pinned by absence of the word in the audit trail.
        self.act(self.session())
        self.assertNotIn("queued", self.audit_outcomes())


class ItIsFailClosedTests(_Case):
    """Neither lane can reopen this door alone, and the default holds."""

    def test_lifting_the_deferral_alone_does_not_send(self):
        # LANE-DB landing the login read does not clear the GT-193 shape.
        with self.deferral_lifted():
            action = self.act(self.session())
        self.assertNotEqual(action and action[0],
                            chat_command_action.SPEED_ACTION_LABEL)

    def test_both_locks_open_is_what_sends(self):
        # The control: without it, the tests above prove only that something
        # somewhere refuses, not that THESE two gates are what hold.
        store = self.store()
        with self.deferral_lifted(), mock.patch.object(
            speed_wire,
            "SHAPES_CLEARED_BY_A_REAL_CLIENT",
            frozenset({(speed_wire.SECTION_ACTOR_ATTR,)}),
        ):
            action = self.act(self.session(store))
        self.assertEqual(action[0], chat_command_action.SPEED_ACTION_LABEL)

    def test_the_deferral_is_the_default_in_the_source_not_a_computed_guess(self):
        # COO 1847 forbids guessing.  `SPEED_LOGIN_READ_LANDED` is a literal a
        # round edits with its evidence named, not a heuristic that could read
        # LANE-DB's module wrong and reopen the door that locked a client.
        self.assertIsInstance(speed_wire.SPEED_LOGIN_READ_LANDED, bool)


if __name__ == "__main__":
    unittest.main()
