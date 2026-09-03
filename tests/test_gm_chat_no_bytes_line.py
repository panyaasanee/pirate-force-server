"""An ACCEPTED GM command that sent nothing says so on the console.

THE DEFECT THIS FILE PINS, measured through the real dispatcher this round
(round `tvbiqc`, all six inputs are reproduced in the round record):

    /warp 2 100 200 -> console: `LANE_GM_CHAT_ACTION warp route=action`
    /say hello      -> console: `LANE_GM_CHAT_ACTION say route=action`
    /lv 10          -> console: `LANE_GM_CHAT_ACTION lv route=action`
    /item 1001 5    -> console: `LANE_GM_CHAT_ACTION item route=action`
    /npc on 5       -> console: `LANE_GM_CHAT_ACTION npc route=action`
    /spawn 7        -> console: `LANE_GM_CHAT_ACTION spawn route=action`

and, in every one of those six, NOT ONE BYTE went to the client.  The route
line is printed before any handler runs -- it has always meant "this route
was reached" and nothing more -- so the last thing the console said about a
command that did nothing was a line that reads like success.  A REFUSED
command was better served than an accepted one: `/warp 9999` prints a scene
list, `/warp island` prints a usage line, and `/warp 2 100 200` -- the one
command that can move a character on screen, and the subject of `GT-128` --
printed a line an operator would read as "sent".

WHO PAYS: an attended tester types the warp, nothing moves, and the console
cannot separate "the version gate withheld the frame" (wiring fine, RE open)
from "the client ignored a frame we did send" (wiring fine, client answer)
from "the route is dead" (wiring broken).  The first two are PASS-shaped for
the wiring and the third is not.

WHAT IS NOT CLAIMED HERE
------------------------
Nothing in this file claims a byte reached a client, that anyone at a game
client sees any of this, or that any command became executable.  The line
goes to the SERVER HOST'S stderr and nowhere else -- the same rung
`_print_command_refusal_way_out` and `_print_warp_way_out` sit on, and the
same one `COO-DECISION 20260829_1344` ruled is the operator's, not the
tester's.  What changed is that an operator watching that console can now
tell a shut gate from a dead route; the tester at the client is exactly
where they were.
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

from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command as gm_commands_chat  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import commands as gm_commands  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import login_scene_stage  # noqa: E402
from pirateforce_foundation.gm import teleport_wire  # noqa: E402
from pirateforce_foundation.gm import warp_executor  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

# Not the real one -- RE-129's measured byte is 0, which is now the SHIPPED
# constant (COO-DECISION 20260830_1645/1742).  This value only ever opens the
# gate to some OTHER version for the audit-failure case, which needs a frame
# to exist before it can be dropped, and must never be readable later as
# evidence about the real client's accepted version.
UNPROVEN_TEST_VERSION = 7

TOKEN = chat_command_action.WITHHELD_CONSOLE_TOKEN


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
    # `identity_lo`/`identity_hi` are NOT decoration.  Before round `c637o1`
    # this double carried only `.id`, so every no-bytes line in this file
    # rendered `identity=none` and the file could not have noticed if the
    # field had been dropped, swapped or hardcoded (pf-adversary D6).
    def __init__(self, position=None, character_id=77, identity_lo=5, identity_hi=9):
        self.position = position
        self.id = character_id
        self.identity_lo = identity_lo
        self.identity_hi = identity_hi


class FakeFoundation:
    def __init__(self, selected=None):
        self.selected = selected


class FakeSession:
    def __init__(self, token="GM_ONE", position=None):
        self.token = token
        self.events = []
        self.foundation = FakeFoundation(FakeSelected(position))


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
        self.login_scene_config_path = self.tmp / "config" / "gm_login_scene.json"
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def act(self, text, session=None, **kwargs):
        """One typed line through the real route; returns (action, stderr)."""
        session = session if session is not None else self.session()
        kwargs.setdefault("config_path", str(self.config_path))
        kwargs.setdefault("log_path", str(self.log_path))
        kwargs.setdefault(
            "login_scene_config_path", str(self.login_scene_config_path)
        )
        err = io.StringIO()
        out = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            action = chat_command_action.make_gm_chat_command_action(
                session, make_chat_payload(text), self.legacy, **kwargs
            )
        self.assertEqual(
            out.getvalue(),
            "",
            "no GM console line may reach stdout -- that is the lane_hooks"
            " --json artifact incident this lane already paid for once",
        )
        return action, err.getvalue()

    def session(self, token=None, position=None):
        return FakeSession(
            token=self.GM_ACCOUNT if token is None else token,
            position=FakePosition() if position is None else position,
        )

    def lines(self, stderr: str, token: str):
        return [ln for ln in stderr.splitlines() if ln.startswith(token)]

    def close_the_version_gate(self):
        """Force the ForcePos gate shut. Since COO-DECISION
        20260830_1645/1742 the shipped constant is `0`, not `None`, so a test
        that means to walk the withheld `/warp` branch must patch this in
        explicitly rather than getting it for free.

        IT ALSO HOLDS THE POLICY GATE OPEN (`COO-DECISION 20260903_1744` item
        3).  `warp_executor.WARP_SAME_SCENE_FORCE_POS_AUTHORIZED` ships False
        after R306 measured this frame closing the client, and it is read
        BEFORE the version byte -- so a test isolating the version gate that
        left it shut would assert on the policy refusal instead, and go green
        with its own branch unreached.
        """
        return self._force_pos_gates(None)

    def open_the_version_gate(self):
        """The sibling: both gates open, for a `/warp <n> x y` that composes."""
        return self._force_pos_gates(UNPROVEN_TEST_VERSION)

    @staticmethod
    @contextlib.contextmanager
    def _force_pos_gates(version):
        with mock.patch.object(
            teleport_wire, "FORCE_POS_VITAL_VERSION_CONFIRMED", version
        ), mock.patch.object(
            warp_executor, "WARP_SAME_SCENE_FORCE_POS_AUTHORIZED", True
        ):
            yield


class TheSixSilentCommandsTests(_Case):
    """Each accepted command that sends nothing prints exactly one line.

    ~~SIX~~ -- pf-adversary D11, round `07kjfd`: a shipped boot now has a
    SEVENTH silent shape, `/warp <n> <x> <y>`, shut by
    `warp_executor.WARP_SAME_SCENE_FORCE_POS_AUTHORIZED` after R306 measured
    that frame closing the client (`COO-DECISION 20260903_1744` item 3).
    The class name and the `/warp 2 100 200` row below are kept as they are
    because this class is about the VERSION gate's silence and forces that
    gate shut itself -- the row's `why=withheld_force_pos_vital_version` is
    the word that configuration produces, not the word a real boot produces.
    The shipped word is graded in `tests/test_gm_chat_command_action.py::
    SameSceneForcePosClosedTests`, which patches no gate at all.
    """

    CASES = (
        ("/warp 2 100 200", "warp", "withheld_force_pos_vital_version"),
        ("/say hello", "say", "withheld_gm_global_message_vital_version"),
        ("/lv 10", "lv", "refused_no_wire_path"),
        ("/item 1001 5", "item", "refused_no_wire_path"),
        ("/npc on 5", "npc", "refused_no_wire_path"),
        ("/spawn 7", "spawn", "refused_no_wire_path"),
    )

    def test_each_one_says_it_sent_nothing_and_names_the_blocker(self):
        for typed, name, why in self.CASES:
            with self.subTest(typed=typed):
                gm_dispatch.reset_rate_limit_state_for_tests()
                # /warp's own gate is forced shut -- shipped at 0 since
                # COO-DECISION 20260830_1645/1742, so every one of these six
                # cases must stay silent even though /warp itself now
                # composes when unpatched. Harmless for the other five.
                with self.close_the_version_gate():
                    action, err = self.act(typed)
                self.assertIsNone(action, "no bytes may go out for any of these")
                said = self.lines(err, TOKEN)
                self.assertEqual(len(said), 1, err)
                self.assertIn(f"command={name} ", said[0])
                self.assertIn(f"why={why} ", said[0])
                # The blocker half is what makes the line worth printing: a
                # line that says "nothing happened" without naming what
                # would change that is the silence with extra steps.
                self.assertIn("blocked_on='", said[0])
                self.assertNotIn(
                    chat_command_action.NO_BLOCKER_RECORDED,
                    said[0],
                    "these six outcomes all have a named blocker",
                )

    def test_the_blocker_is_the_one_that_belongs_to_that_outcome(self):
        # A mutant that prints one hardcoded sentence for every command
        # passes the test above and is useless to the operator it is for.
        # /warp's gate forced shut for the same reason as the test above.
        with self.close_the_version_gate():
            _, warp_err = self.act("/warp 2 100 200")
        gm_dispatch.reset_rate_limit_state_for_tests()
        _, say_err = self.act("/say hello")
        gm_dispatch.reset_rate_limit_state_for_tests()
        _, lv_err = self.act("/lv 10")
        self.assertIn("RE-129", warp_err)
        self.assertNotIn("RE-129", say_err)
        self.assertIn("gm/say_wire.py", say_err)
        self.assertNotIn("gm/say_wire.py", warp_err)
        self.assertIn("CORE-REQUEST-GM", lv_err)
        self.assertNotIn("CORE-REQUEST-GM", warp_err)

    def test_the_route_line_is_still_there(self):
        # The new line is an ADDITION.  `LANE_GM_CHAT_ACTION` is what an
        # attended GT-127 run greps for, and a round that "cleaned it up"
        # would fail that drill from the tester's chair, not here.
        _, err = self.act("/lv 10")
        self.assertEqual(
            len(self.lines(err, chat_command_action.CONSOLE_TOKEN)), 1, err
        )


class TheIdentityFieldsOnEveryCommandTests(_Case):
    """The two fields `COO-DECISION 0147` asked for, on the SHARED line.

    THE GAP THIS CLOSES (pf-adversary round `c637o1`, D6).  Round `c637o1`
    added `character_id=` and `identity=` to `_print_no_bytes_way_out` and
    tested them only through `/speed`, in another file.  This line is shared
    by six other commands; deleting both fields killed ZERO tests here, in
    the file that owns the line's format.  The fields are pinned here now,
    for every command that reaches the line, not only for the one whose COO
    decision paid for them.

    NONCLAIM, carried from the speed file so it cannot be read off only
    there: these fields name WHICH CHARACTER ROW this connection selected.
    They do not identify a connection -- two connections holding the same
    character render identical fields, and `identity_hi` is `0` for every
    character this server creates.
    """

    def field(self, line, name):
        marker = f" {name}="
        self.assertIn(marker, line)
        return line.split(marker, 1)[1].split(" ", 1)[0]

    def test_every_one_of_the_six_carries_the_row_it_was_typed_on(self):
        for typed, name, _why in TheSixSilentCommandsTests.CASES:
            with self.subTest(typed=typed):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition())
                session.foundation.selected = FakeSelected(
                    position=FakePosition(), character_id=101,
                    identity_lo=202, identity_hi=303,
                )
                with self.close_the_version_gate():
                    _, err = self.act(typed, session=session)
                said = self.lines(err, TOKEN)
                self.assertEqual(len(said), 1, err)
                self.assertEqual(self.field(said[0], "character_id"), "101")
                # Asymmetric, so a swapped pair reads `303:202` and fails.
                self.assertEqual(self.field(said[0], "identity"), "202:303")

    def test_a_connection_with_nothing_selected_says_none_on_this_line_too(self):
        session = FakeSession()
        session.foundation.selected = None
        _, err = self.act("/lv 10", session=session)
        said = self.lines(err, TOKEN)
        self.assertEqual(len(said), 1, err)
        self.assertEqual(self.field(said[0], "character_id"), "none")
        self.assertEqual(self.field(said[0], "identity"), "none")

    def test_the_account_token_is_not_reused_as_either_field(self):
        # Value equality, not substring absence: `identity='GM_ONE'` defeated
        # the substring form with one quote character (pf-adversary D2).
        session = FakeSession(position=FakePosition())
        session.foundation.selected = FakeSelected(
            position=FakePosition(), character_id=101,
            identity_lo=202, identity_hi=303,
        )
        _, err = self.act("/lv 10", session=session)
        line = self.lines(err, TOKEN)[0]
        self.assertIn(f"account='{self.GM_ACCOUNT}'", line)
        self.assertEqual(self.field(line, "character_id"), "101")
        self.assertEqual(self.field(line, "identity"), "202:303")

    def test_the_staged_line_does_not_grow_them(self):
        # The staged warp is the one accepted command that sends nothing and
        # is not a disappointment; its line answers a different question
        # (which scene, what to do next) and must not drift into carrying
        # this one's fields by copy-paste.  `/warp 278` is the input
        # `TheStagedWarpTests` already proves reaches the staged printer, so
        # this assertion cannot go vacuous if that behaviour changes.
        action, err = self.act("/warp 278")
        self.assertIsNone(action)
        staged = self.lines(err, chat_command_action.STAGED_CONSOLE_TOKEN)
        self.assertEqual(len(staged), 1, err)
        self.assertNotIn("identity=", staged[0])
        self.assertNotIn("character_id=", staged[0])


class TheServerSideDropLineTests(_Case):
    """A well-formed GM command the SERVER dropped says so (D1).

    pf-adversary measured the hole this closes: 25 rapid `/speed 400` frames
    printed 20 route lines and then NOTHING for the five the limiter
    dropped -- not `GM_CHAT_NO_BYTES_SENT` (no handler ran) and not
    `GM_CHAT_COMMAND_REFUSED` (not a typing mistake).  `COO-DECISION
    2026-09-02T01:47+07:00` names that silence as the forbidden outcome.

    WHAT IS STILL SILENT, pinned here on purpose so no later reader takes
    this class as "nothing vanishes any more": a non-GM's chat, a GM's
    ordinary conversation, an unreadable allowlist and a malformed frame.
    Every one of those is decided ABOVE the `is_gm` check and this lane must
    not learn to speak about them.
    """

    DROPPED = chat_command_action.DROPPED_CONSOLE_TOKEN

    def test_the_rate_limiter_no_longer_eats_a_command_in_silence(self):
        seen = []
        for _ in range(gm_dispatch.RATE_LIMIT_MAX_CALLS_PER_WINDOW + 3):
            _, err = self.act("/lv 10")
            seen.append(err)
        dropped = [e for e in seen if self.lines(e, self.DROPPED)]
        self.assertEqual(len(dropped), 3, "".join(seen))
        line = self.lines(dropped[0], self.DROPPED)[0]
        self.assertIn("why=rate_limited ", line)
        self.assertIn("blocked_on='", line)
        self.assertNotIn(chat_command_action.NO_BLOCKER_RECORDED, line)
        # Same identity contract as the sibling line.
        self.assertIn("character_id=77", line)
        self.assertIn("identity=5:9", line)

    def test_a_dropped_command_gets_exactly_one_line_not_two(self):
        # The two refusal printers are keyed on disjoint reason sets; a
        # refusal that earned one of them must never earn the other.
        for _ in range(gm_dispatch.RATE_LIMIT_MAX_CALLS_PER_WINDOW):
            self.act("/lv 10")
        _, err = self.act("/lv 10")
        self.assertEqual(len(self.lines(err, self.DROPPED)), 1, err)
        self.assertEqual(
            len(self.lines(err, chat_command_action.COMMAND_REFUSED_CONSOLE_TOKEN)),
            0,
            err,
        )
        self.assertEqual(len(self.lines(err, TOKEN)), 0, err)

    def test_a_typo_still_gets_the_typo_line_and_not_this_one(self):
        _, err = self.act("/warp island")
        self.assertEqual(len(self.lines(err, self.DROPPED)), 0, err)
        self.assertEqual(
            len(self.lines(err, chat_command_action.COMMAND_REFUSED_CONSOLE_TOKEN)),
            1,
            err,
        )

    def test_a_non_gm_account_is_still_completely_silent(self):
        # The founding rule, re-checked against the printer added this round:
        # this lane never says a word about a non-GM's chat.
        session = self.session(token="DECKHAND")
        _, err = self.act("/lv 10", session=session)
        self.assertEqual(err, "", err)

    def test_an_ordinary_sentence_from_a_gm_is_still_silent(self):
        _, err = self.act("just talking to a friend here")
        self.assertEqual(self.lines(err, self.DROPPED), [], err)

    def test_an_unwritable_audit_log_says_so_instead_of_vanishing(self):
        # `log_path` points at a directory that cannot be created, so
        # `log_gm_command` raises OSError below the is_gm check.
        blocker = self.tmp / "not_a_dir"
        blocker.write_text("", encoding="utf-8")
        _, err = self.act("/lv 10", log_path=str(blocker / "sub" / "log.ndjson"))
        line = self.lines(err, self.DROPPED)
        self.assertEqual(len(line), 1, err)
        self.assertIn("why=command_log_write_failed_", line[0])
        self.assertIn("cannot record", line[0])

    def test_every_drop_blocker_is_one_ascii_line_within_the_cap(self):
        for prefix, sentence in chat_command_action.SERVER_DROP_BLOCKERS:
            with self.subTest(prefix=prefix):
                self.assertEqual(sentence, sentence.strip())
                self.assertNotIn("\n", sentence)
                sentence.encode("ascii")
                self.assertLessEqual(
                    len(sentence), chat_command_action.MAX_CONSOLE_HINT_LENGTH
                )

    def test_every_server_side_drop_reason_has_a_sentence(self):
        # The completeness half: a reason added to the tuple in
        # `chat_command.py` without a sentence here would print
        # `no blocker recorded` for exactly the state an operator most needs
        # explained.
        for reason in gm_commands_chat.SERVER_SIDE_DROP_REFUSALS:
            with self.subTest(reason=reason):
                self.assertTrue(
                    any(
                        reason.startswith(prefix)
                        for prefix, _ in chat_command_action.SERVER_DROP_BLOCKERS
                    )
                )


class ItNeverPrintsWhatWasTypedTests(_Case):
    """The founding rule of every console line this module writes."""

    def test_a_say_body_never_reaches_the_console(self):
        _, err = self.act("/say NEEDLEALPHA NEEDLEBETA")
        self.assertIn(TOKEN, err)
        self.assertNotIn("NEEDLE", err)

    def test_command_arguments_never_reach_the_console(self):
        _, err = self.act("/item 424242 77771")
        self.assertIn(TOKEN, err)
        self.assertNotIn("424242", err)
        self.assertNotIn("77771", err)

    def test_a_name_outside_the_vocabulary_renders_unnamed(self):
        # A `GmCommand` is accepted "regardless of source" everywhere in this
        # lane, so the NAME is caller-chosen text until this line checks it.
        # The hostile value is also a line forgery: without the membership
        # check it would spell a second console line carrying another lane's
        # grep token.
        session = self.session()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chat_command_action._print_no_bytes_way_out(
                session,
                self.GM_ACCOUNT,
                "warp\nGM_CHAT_WARP_REFUSED account='x' scene_id=1",
                chat_command_action.OUTCOME_NO_WIRE_PATH,
            )
        printed = err.getvalue()
        self.assertEqual(len(printed.splitlines()), 1, printed)
        self.assertIn("command=unnamed ", printed)
        self.assertNotIn("GM_CHAT_WARP_REFUSED", printed)

    def test_a_newline_in_the_account_cannot_forge_a_line(self):
        session = self.session()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chat_command_action._print_no_bytes_way_out(
                session,
                "GM_ONE\nGM_CHAT_WARP_REFUSED account='x'",
                "lv",
                chat_command_action.OUTCOME_NO_WIRE_PATH,
            )
        printed = err.getvalue()
        self.assertEqual(len(printed.splitlines()), 1, printed)
        self.assertIn("\\n", printed)


class NoSecondLineTests(_Case):
    """A refusal that already explained itself is not explained twice."""

    def test_an_unknown_scene_keeps_its_scene_list_and_gains_nothing(self):
        action, err = self.act("/warp 9999")
        self.assertIsNone(action)
        self.assertEqual(
            len(self.lines(err, chat_command_action.WARP_REFUSED_CONSOLE_TOKEN)),
            1,
            err,
        )
        self.assertEqual(self.lines(err, TOKEN), [], err)

    def test_a_sanctioned_but_barred_scene_keeps_its_blocker_line(self):
        # Round R249 (chief, gate-red repair of `pirate-force-server#332`)
        # landed lane A's real scene-126 row with a pinned spawn, so
        # `CORE-REQUEST-GM-038`'s single-use widening now ADMITS 126 --
        # `/warp 126` stages instead of refusing.  The "blocker=" line only
        # ever prints for `REASON_SANCTIONED_NOT_YET_REACHABLE`
        # (`chat_command_action.py`), so force exactly that outcome instead
        # of relying on 126 staying unreachable forever.
        result = mock.Mock(
            staged=False,
            reason=login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE,
            previous_scene_id=None,
        )
        with mock.patch.object(
            login_scene_stage, "stage_login_scene", return_value=result
        ):
            action, err = self.act("/warp 126")
        self.assertIsNone(action)
        self.assertIn("blocker=", err)
        self.assertEqual(self.lines(err, TOKEN), [], err)

    def test_a_stage_refusal_the_scene_printer_declines_still_gets_a_line(self):
        # `_print_warp_way_out` answers only DESTINATION_SHAPED_REASONS -- a
        # different destination cannot fix a server-side fault, so naming
        # one would blame the tester's typing.  That is right, and it used to
        # mean those refusals printed NOTHING.  This is the case that fails
        # if a later round decides the outcome word alone can tell whether a
        # line was printed.
        reason = login_scene_stage.REASON_WRITE_FAILED
        self.assertNotIn(reason, login_scene_stage.DESTINATION_SHAPED_REASONS)
        result = mock.Mock(staged=False, reason=reason, previous_scene_id=None)
        with mock.patch.object(
            login_scene_stage, "stage_login_scene", return_value=result
        ):
            action, err = self.act("/warp 278")
        self.assertIsNone(action)
        self.assertEqual(
            self.lines(err, chat_command_action.WARP_REFUSED_CONSOLE_TOKEN), [], err
        )
        said = self.lines(err, TOKEN)
        self.assertEqual(len(said), 1, err)
        self.assertIn(f"why=refused_stage_{reason} ", said[0])
        # pf-adversary D4: this used to print `no blocker recorded` -- these
        # five are named constants with knowable remedies, not an exception
        # family, and the boot that reaches them is the boot that needs the
        # sentence most.
        self.assertNotIn(chat_command_action.NO_BLOCKER_RECORDED, said[0])
        self.assertIn("gm_login_scene.json", said[0])

    def test_a_stage_refusal_that_raised_gets_the_type_name(self):
        with mock.patch.object(
            login_scene_stage, "stage_login_scene", side_effect=OSError("disk")
        ):
            action, err = self.act("/warp 278")
        self.assertIsNone(action)
        said = self.lines(err, TOKEN)
        self.assertEqual(len(said), 1, err)
        self.assertIn("why=refused_stage_OSError ", said[0])
        # The exception's MESSAGE is not a field on this line -- type names
        # only, the rule this module states for every event it emits.
        self.assertNotIn("disk", err)


class ThingsThatMustStaySilentTests(_Case):
    def test_a_staged_cross_scene_warp_is_not_called_no_bytes(self):
        action, err = self.act("/warp 278")
        self.assertIsNone(action)
        self.assertEqual(self.lines(err, TOKEN), [], err)
        staged = json.loads(
            self.login_scene_config_path.read_text(encoding="utf-8")
        )["gm_login_scene"]
        self.assertEqual(staged[self.GM_ACCOUNT], 278)

    def test_a_staged_warp_that_carried_coordinates_is_also_silent(self):
        # Since round `fftpji` (COO-DECISION 2026-08-31T14:41+07:00), a
        # cross-scene warp WITH coordinates fires live instead of staging --
        # so reaching the stage-with-coordinates shape this test is about
        # needs the authorization flag off, the kill-switch path back to
        # the pre-1441 behaviour this test still guards.
        with mock.patch.object(
            warp_executor, "WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED", False
        ):
            action, err = self.act("/warp 278 100 200")
        self.assertIsNone(action)
        self.assertEqual(self.lines(err, TOKEN), [], err)

    def test_a_mistyped_command_keeps_its_usage_line_and_gains_nothing(self):
        action, err = self.act("/warp island")
        # ~~`assertIsNone(action)`~~ -- struck since COO-DECISION
        # 2026-09-02T06:47+07:00 (`pf_bridge/notes_to_chief/consumed/
        # 20260902_0647_COO-DECISION-typo-layer-notice-is-TYPO-REFUSED-12-
        # ascii-after-p1.md`): a mistyped command now answers the connection
        # with a twelve-character `TYPO REFUSED` notice on 0xAC52.  This
        # test's own subject is the CONSOLE, and both of its console claims
        # below are unchanged: exactly one usage line, and no no-bytes line.
        self.assertEqual(
            action[0], chat_command_action.TYPO_REFUSED_NOTICE_ACTION_LABEL
        )
        self.assertEqual(
            len(
                self.lines(err, chat_command_action.COMMAND_REFUSED_CONSOLE_TOKEN)
            ),
            1,
            err,
        )
        self.assertEqual(self.lines(err, TOKEN), [], err)

    def test_an_ordinary_sentence_prints_nothing_at_all(self):
        # The founding rule: a GM's conversation is not decoded, matched or
        # written anywhere.  A backstop that fired here would put a console
        # line under every sentence anyone types.
        action, err = self.act("hello there, sailor")
        self.assertIsNone(action)
        self.assertEqual(err, "")

    def test_a_non_gm_account_gets_no_line_either(self):
        action, err = self.act("/lv 10", session=self.session(token="DECKHAND"))
        self.assertIsNone(action)
        self.assertEqual(self.lines(err, TOKEN), [], err)


class TheStagedWarpTests(_Case):
    """The one accepted command that sends nothing and is not a disappointment.

    pf-adversary D3: the first version of this round printed NOTHING for a
    staged cross-scene warp, which left the hole open for the only `/warp`
    form that changes anything today -- and the round's own claim said it
    was closed.
    """

    STAGED = chat_command_action.STAGED_CONSOLE_TOKEN

    def test_it_names_the_scene_and_the_next_step(self):
        action, err = self.act("/warp 278")
        self.assertIsNone(action)
        said = self.lines(err, self.STAGED)
        self.assertEqual(len(said), 1, err)
        self.assertIn("scene_id=278 ", said[0])
        self.assertIn("coordinates=none ", said[0])
        # ~~`assertIn("log out and log back in", said[0])`~~ -- struck by
        # `COO-DECISION 20260903_2050` item 2.  The relog fact survives in
        # substance (the tail still names it) but it no longer arrives
        # without the REASON no bytes went out, which is what the owner read
        # as "nothing happened".
        #
        # THE SENTENCE IS SPELLED OUT HERE, not fetched from the function
        # that built the line (pf-adversary, round `spt6fv`, D5, MEASURED).
        # The first version of this assertion compared `staged_next_step(...)`
        # against a line built BY `staged_next_step`, so mutants that made the
        # words say the OPPOSITE of the truth -- "this scene HAS a confirmed
        # spawn point", "the next login for this account is unaffected" --
        # passed the entire suite.  A literal is the only thing that can tell
        # the intended sentence from whatever the code happens to emit.
        self.assertIn(
            "next='this scene has no confirmed spawn point, so no teleport"
            " could be sent; the next login for this account is staged to"
            " start in it'",
            said[0],
        )
        # The withdrawn sentence must not come back anywhere on this line.
        self.assertNotIn("log out and log back in", err)
        # It is NOT the no-bytes token: an effect is on disk.
        self.assertEqual(self.lines(err, TOKEN), [], err)

    def test_a_markerless_stage_says_why_no_frame_could_be_sent(self):
        # `COO-DECISION 20260903_2050` item 1 held the markerless scenes shut
        # (R306 measured a coordinates-bearing warp frame CLOSING the client),
        # so the reason is the only thing this lane may add here -- and it is
        # the half the struck sentence never carried.  Pinned on its own, as a
        # literal, so a future rewording of either tail cannot quietly drop
        # the reason and leave the line back where `PANYA-DECISION 1800`
        # found it.
        _, err = self.act("/warp 278")
        said = self.lines(err, self.STAGED)
        self.assertEqual(len(said), 1, err)
        self.assertIn(
            "this scene has no confirmed spawn point, so no teleport could"
            " be sent",
            said[0],
        )

    def test_a_same_scene_stage_does_not_recommend_a_pointless_relog(self):
        # THE MUTANT THIS TEST KILLS is the single-sentence printer: hardcode
        # the cross-scene tail (or restore the struck sentence) and a GM
        # standing in markerless scene 278 who types `/warp 278` is told her
        # NEXT LOGIN will start in it -- true, useless, and, while the logout
        # buttons are still refused (UI-A/UI-B), the most expensive no-op this
        # console can recommend.  `COO-DECISION 20260903_2050` item 2 is
        # exactly this shape.
        _, err = self.act("/warp 278", session=self.session(
            position=FakePosition(scene_id=278)
        ))
        said = self.lines(err, self.STAGED)
        self.assertEqual(len(said), 1, err)
        self.assertIn(
            "next='this scene has no confirmed spawn point, so no teleport"
            " could be sent; you are standing in it already, so a relog would"
            " change nothing'",
            said[0],
        )
        self.assertNotIn("is staged to start in it", said[0])
        self.assertNotIn("log out and log back in", err)

    def test_the_same_scene_claim_names_the_belief_it_rests_on(self):
        # pf-adversary, round `spt6fv`, D2, MEASURED on the real dispatcher:
        # `runtime.py`'s `_gm_warp_resync_selected_scene` rewrites
        # `selected.position.scene_id` to a cross-scene warp's DESTINATION at
        # queue time with nothing from the client confirming the arrival, so
        # "you are standing in it already" can be the server's belief rather
        # than a fact -- and this line, unlike its
        # `GM_CHAT_SAME_SCENE_TELEPORT_SENT` sibling, made the STRONGER claim
        # with no basis label at all.  Drop the field and this goes red.
        _, err = self.act("/warp 278", session=self.session(
            position=FakePosition(scene_id=278)
        ))
        said = self.lines(err, self.STAGED)
        self.assertEqual(len(said), 1, err)
        self.assertIn("basis=server_believed_scene ", said[0])

    def test_a_coordinates_warp_is_never_blamed_on_a_missing_marker(self):
        # THE DEFECT THIS TEST PINS shipped in this round's first commit
        # (pf-adversary, round `spt6fv`, D1, MEASURED).  The reason was
        # derived from `warp_no_coords_live_target(scene)` -- a fact about
        # what the DESTINATION lacks -- and printed in the grammar of "why did
        # THIS COMMAND send nothing".  Those come apart the moment x/y are
        # typed: with `WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED` down,
        # `/warp 997 100 200` from scene 5 stages and was told scene 997 has
        # no confirmed spawn point -- yet the SAME command with the flag up
        # sends a real 73-byte TeleportVital, because a coordinates-bearing
        # warp never needed the marker.  The operator would have gone hunting
        # a spawn point for 997 and nothing would have changed.
        #
        # Scene 997 rather than 278 on purpose: 278 refuses this command for
        # an unrelated ground-extent reason, which is what let the first
        # version of this pair look correct while asserting a falsehood.
        self.assertIsNone(warp_executor.warp_no_coords_live_target(997))
        with mock.patch.object(
            warp_executor, "WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED", False
        ):
            _, err = self.act("/warp 997 100 200", session=self.session(
                position=FakePosition(scene_id=5)
            ))
        said = self.lines(err, self.STAGED)
        self.assertEqual(len(said), 1, err)
        self.assertIn(
            "the live teleport route for this scene is shut, so no teleport"
            " could be sent",
            said[0],
        )
        self.assertNotIn("no confirmed spawn point", said[0])
        self.assertIn("coordinates=ignored ", said[0])

    def test_a_marker_backed_scene_is_not_told_it_has_no_spawn_point(self):
        # The same defect from the other side: with the flag down, a
        # MARKER-BACKED scene stages too, and blaming a missing spawn point
        # would send an operator hunting a marker already in the registry.
        self.assertIsNotNone(
            warp_executor.warp_no_coords_live_target(2),
            "scene 2 must be marker-backed for this test to mean anything",
        )
        with mock.patch.object(
            warp_executor, "WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED", False
        ):
            _, err = self.act("/warp 2 100 200", session=self.session(
                position=FakePosition(scene_id=5)
            ))
        said = self.lines(err, self.STAGED)
        self.assertEqual(len(said), 1, err)
        self.assertIn(
            "the live teleport route for this scene is shut, so no teleport"
            " could be sent",
            said[0],
        )
        self.assertNotIn("no confirmed spawn point", said[0])

    def test_a_bare_warp_into_a_markerless_scene_still_blames_the_spawn(self):
        # The half that keeps the fix from being "always print the shut-route
        # reason".  A BARE `/warp 278` with the flag down is the one shape
        # where both blockers are true at once, and the marker is the durable
        # one: the flag is a kill switch a decision can lift in an afternoon,
        # while `GT-182` nonclaim 4 has held these scenes shut since it was
        # written.
        with mock.patch.object(
            warp_executor, "WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED", False
        ):
            _, err = self.act("/warp 278", session=self.session(
                position=FakePosition(scene_id=5)
            ))
        said = self.lines(err, self.STAGED)
        self.assertEqual(len(said), 1, err)
        self.assertIn(
            "this scene has no confirmed spawn point, so no teleport could"
            " be sent",
            said[0],
        )

    def test_an_unreadable_registry_does_not_take_the_command_off_the_console(self):
        # pf-adversary, round `spt6fv`, D3, MEASURED.  The first commit asked
        # `warp_no_coords_live_target` a SECOND time, inside `_stage_action`'s
        # argument list, to build a console sentence.  That function catches
        # only `KeyError`/`ValueError` while `world_scene_travel.destination`
        # re-reads the registry from disk on every call, so an `OSError` there
        # escaped `_warp_action` and an ACCEPTED command vanished with no
        # console line at all -- in the module whose founding property is that
        # it never does that.  A diagnostic may never alter dispatch.
        with mock.patch.object(
            chat_command_action,
            "warp_no_coords_live_target",
            side_effect=OSError("registry unreadable"),
        ):
            action, err = self.act("/warp 278")
        self.assertIsNone(action)
        said = self.lines(err, self.STAGED)
        self.assertEqual(len(said), 1, err)
        # ...and it says the one thing that is actually known, rather than
        # guessing which of the other two blockers applied.
        self.assertIn(
            "this scene's spawn point could not be read, so no teleport"
            " could be sent",
            said[0],
        )

    def test_the_printer_defaults_are_the_shipped_shape(self):
        # THE MUTANT THIS TEST KILLS is a flip of `_print_staged_way_out`'s
        # own default arguments (pf-adversary, round `spt6fv`, N6/N7, which
        # SURVIVED the first fix).  It survived honestly: the one dispatch
        # call site passes both arguments explicitly, so no input through the
        # dispatcher can reach the defaults, and the docstring's claim that
        # they are "the shipped shape" was unfalsifiable.  It is a direct call
        # for that reason -- the contract is real (a future call site that
        # forgets an argument must understate rather than invent), and an
        # unreachable contract is exactly the kind this file has been bitten
        # by before.
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chat_command_action._print_staged_way_out(
                self.session(),
                self.GM_ACCOUNT,
                gm_commands.GmCommand("warp", ("278",), "/warp 278"),
                chat_command_action.OUTCOME_STAGED_LOGIN_SCENE,
            )
        printed = err.getvalue()
        self.assertIn(
            "next='this scene has no confirmed spawn point, so no teleport"
            " could be sent; the next login for this account is staged to"
            " start in it'",
            printed,
        )

    def test_every_blocker_sentence_ends_in_the_six_words_a_tester_greps(self):
        # The property an attended tester navigates by: ONE grep finds every
        # staged shape whichever blocker is named, and the clause in front of
        # those six words is the one to act on.  Derived from the shipped
        # tuple rather than from a list retyped here, so a fourth blocker
        # added later cannot skip the property by being forgotten.
        self.assertEqual(
            len(chat_command_action.STAGED_BLOCKER_REASONS),
            len(set(chat_command_action.STAGED_BLOCKER_REASONS)),
        )
        for reason in chat_command_action.STAGED_BLOCKER_REASONS:
            with self.subTest(reason=reason):
                self.assertTrue(
                    reason.endswith("no teleport could be sent"), reason
                )


    def test_it_says_when_the_typed_coordinates_were_dropped(self):
        # The fact that lived nowhere a human would look.  `ForcePos` cannot
        # cross scenes, so `/warp 278 100 200` used to stage the scene and
        # discard the two numbers -- and before this line the only record of
        # that was the ndjson word.  Since round `fftpji` this shape fires
        # live by default (COO-DECISION 1441), so this test forces the
        # authorization flag off to keep exercising the coords-ignored
        # staging path it is about.
        with mock.patch.object(
            warp_executor, "WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED", False
        ):
            action, err = self.act("/warp 278 100 200")
        self.assertIsNone(action)
        said = self.lines(err, self.STAGED)
        self.assertEqual(len(said), 1, err)
        self.assertIn("coordinates=ignored ", said[0])

    def test_a_stage_whose_audit_failed_does_not_claim_a_staged_scene(self):
        # The entry is taken back off disk when its outcome row cannot be
        # written, so a console line saying "log back in to land there"
        # would send the tester to a scene nobody staged.
        with mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            side_effect=OSError("read-only capture directory"),
        ):
            action, err = self.act("/warp 278")
        self.assertIsNone(action)
        self.assertEqual(self.lines(err, self.STAGED), [], err)
        said = self.lines(err, TOKEN)
        self.assertEqual(len(said), 1, err)
        self.assertIn(
            f"why={chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN} ", said[0]
        )

    def test_it_never_prints_a_scene_it_could_not_read(self):
        # A diagnostic may never alter dispatch, and by the time this line
        # runs the config entry is already written.
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chat_command_action._print_staged_way_out(
                self.session(),
                self.GM_ACCOUNT,
                object(),
                chat_command_action.OUTCOME_STAGED_LOGIN_SCENE,
            )
        printed = err.getvalue()
        self.assertEqual(len(printed.splitlines()), 1, printed)
        self.assertIn("scene_id=unknown ", printed)


class TheSameSceneWarpTests(_Case):
    """`PANYA-DECISION 20260903_1800`: the one SENT command that also speaks.

    The owner typed `/warp 2` while standing in scene 2 during R307 and read
    `GM_CHAT_STAGED_NEXT_LOGIN` as "nothing happened" -- correctly, because
    nothing had reached her client.  These tests pin the two halves of the
    fix: the frame goes out, and the console says which kind of warp it was.
    """

    SAME_SCENE = chat_command_action.SAME_SCENE_TELEPORT_CONSOLE_TOKEN

    def test_it_says_the_teleport_was_sent_and_names_the_scene(self):
        action, err = self.act("/warp 2", session=self.session(
            position=FakePosition(scene_id=2)
        ))
        self.assertIsNotNone(action)
        said = self.lines(err, self.SAME_SCENE)
        self.assertEqual(len(said), 1, err)
        self.assertIn("scene_id=2 ", said[0])
        self.assertIn("coordinates=none ", said[0])
        # The no-bytes token must not appear: bytes DID go out.
        self.assertEqual(self.lines(err, TOKEN), [], err)

    def test_the_staged_token_is_not_printed_for_a_same_scene_marker_warp(self):
        # THE MUTANT THIS TEST KILLS is the old routing itself: restore the
        # `target_scene_id != position.scene_id` test on the no-coordinates
        # branch in `_warp_action` and this line comes back, which is exactly
        # the sentence `PANYA-DECISION 1800` forbids for this shape.
        action, err = self.act("/warp 2", session=self.session(
            position=FakePosition(scene_id=2)
        ))
        self.assertIsNotNone(action)
        self.assertEqual(
            self.lines(err, chat_command_action.STAGED_CONSOLE_TOKEN), [], err
        )
        # ~~`assertNotIn("log out and log back in", err)`~~ -- the sentence
        # this pinned against no longer exists anywhere in the module
        # (`COO-DECISION 20260903_2050` item 2), so asserting its absence
        # would pass on a module that had lost the staged line entirely.
        # Pinned against the sentence that REPLACED it instead, which is what
        # `PANYA-DECISION 1800` forbids for this shape -- as a LITERAL, since
        # a negative assertion fetched from the module goes vacuous the moment
        # the constant is emptied or reworded (pf-adversary, round `spt6fv`,
        # D5).
        self.assertNotIn("no teleport could be sent", err)

    def test_a_cross_scene_bare_warp_does_not_borrow_this_token(self):
        # The token exists to tell the two apart on one console. A cross-scene
        # `/warp 4` from scene 2 sends the same label and must stay silent
        # here, or the line means nothing.
        action, err = self.act("/warp 4", session=self.session(
            position=FakePosition(scene_id=2)
        ))
        self.assertIsNotNone(action)
        self.assertEqual(self.lines(err, self.SAME_SCENE), [], err)

    def test_a_same_scene_warp_whose_audit_failed_claims_no_teleport(self):
        # The frame is dropped when its outcome row cannot be written, so a
        # line saying "you were moved" would name a move that never left.
        with mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            side_effect=OSError("read-only capture directory"),
        ):
            action, err = self.act("/warp 2", session=self.session(
                position=FakePosition(scene_id=2)
            ))
        self.assertIsNone(action)
        self.assertEqual(self.lines(err, self.SAME_SCENE), [], err)
        said = self.lines(err, TOKEN)
        self.assertEqual(len(said), 1, err)

    def test_it_never_prints_a_scene_it_could_not_read(self):
        # Same contract as `_print_staged_way_out`'s own: a diagnostic may
        # never alter dispatch, and by the time this line runs the frame is
        # already on its way.
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chat_command_action._print_same_scene_teleport(
                self.session(), self.GM_ACCOUNT, object()
            )
        printed = err.getvalue()
        self.assertEqual(len(printed.splitlines()), 1, printed)
        self.assertIn("scene_id=unknown ", printed)

    def test_the_token_is_its_own_grep(self):
        # Same rule the no-bytes token keeps: an operator greps one question
        # at a time, and a token sharing a prefix with another returns the
        # other's lines too.
        for other in (
            chat_command_action.CONSOLE_TOKEN,
            chat_command_action.STAGED_CONSOLE_TOKEN,
            chat_command_action.WARP_REFUSED_CONSOLE_TOKEN,
            TOKEN,
        ):
            with self.subTest(other=other):
                self.assertFalse(self.SAME_SCENE.startswith(other))
                self.assertFalse(other.startswith(self.SAME_SCENE))

    def test_the_token_is_spelled_the_way_the_decision_spells_it(self):
        # pf-adversary D5: every other test in this class reads the token
        # THROUGH the constant, so renaming the constant's VALUE left the
        # whole suite green while an attended round greping COO's and
        # PANYA's spelling found nothing. The literal is the contract.
        self.assertEqual(
            chat_command_action.SAME_SCENE_TELEPORT_CONSOLE_TOKEN,
            "GM_CHAT_SAME_SCENE_TELEPORT_SENT",
        )

    def test_the_line_says_what_it_did_and_refuses_the_two_claims_it_cannot_make(self):
        # pf-adversary D1, MEASURED: the first draft said "you were moved"
        # (a claim about her screen, from a wire fact) and "nothing was
        # staged for the next login" (a claim about account state this
        # printer never reads -- `/warp 278` then `/warp 1` left 278 staged
        # while this line denied it). D9: nothing graded the sentence at all.
        _, err = self.act("/warp 2", session=self.session(
            position=FakePosition(scene_id=2)
        ))
        said = self.lines(err, self.SAME_SCENE)[0]
        self.assertIn(
            "next='a teleport frame for this scene own pinned spawn left the"
            " server; this line does not say the client moved, and this"
            " command wrote no next-login scene'",
            said,
        )
        self.assertNotIn("you were moved", said)
        self.assertNotIn("nothing was staged", said)

    def test_the_line_names_what_same_scene_was_decided_from(self):
        # pf-adversary D2, MEASURED: "same scene" is decided against
        # `selected.position.scene_id`, which `runtime.py` rewrites to a
        # cross-scene warp's DESTINATION at queue time with nothing from the
        # client confirming it -- so a repeated `/warp 5` gets this token.
        # The lane cannot fix that from its own zone; it can refuse to hide
        # it on the line the tester greps.
        _, err = self.act("/warp 2", session=self.session(
            position=FakePosition(scene_id=2)
        ))
        said = self.lines(err, self.SAME_SCENE)[0]
        self.assertIn("basis=server_believed_scene ", said)
        self.assertEqual(
            chat_command_action.SAME_SCENE_BASIS_FIELD, "server_believed_scene"
        )

    def test_a_client_backed_scene_upgrades_the_basis_on_the_sent_line(self):
        # chief's `client_confirmed_scene` landed (letter `20260903_2306`,
        # answering `CORE-REQUEST-GM-051` item 3), and both docstrings
        # promised the two lines would change basis together the day it did.
        # A connection whose client has actually reported from scene 2 gets
        # the stronger word.
        session = self.session(position=FakePosition(scene_id=2))
        session.client_confirmed_scene = 2
        _, err = self.act("/warp 2", session=session)
        said = self.lines(err, self.SAME_SCENE)[0]
        self.assertIn("basis=client_confirmed_scene ", said)

    def test_the_client_backed_scene_outranks_the_servers_own_relabel(self):
        # THE DEFECT THE FIELD EXISTS TO CLOSE (pf-adversary D2), now
        # measurable at this layer: `_gm_warp_resync_selected_scene` has
        # rewritten `position.scene_id` to 5 (the destination of a warp the
        # client never confirmed), while the last frame the client actually
        # sent was from scene 1.  The server's own label would call this
        # "same scene"; the client's would not, and the client's wins.
        session = self.session(position=FakePosition(scene_id=5))
        session.client_confirmed_scene = 1
        action, err = self.act("/warp 5", session=session)
        # The frame still leaves -- routing is untouched by the basis, and
        # `/warp 5` to a marker-backed scene sends either way.  What changes
        # is that the console no longer TELLS her she is already in scene 5
        # on the strength of a label the server wrote for itself.
        self.assertIsNotNone(action)
        self.assertEqual(self.lines(err, self.SAME_SCENE), [], err)
        self.assertNotIn("you are standing in it already", err)

    def test_a_client_that_has_never_spoken_keeps_the_weaker_word(self):
        # chief chose `None` for "the client has told us nothing" over "the
        # scene of the row at login" deliberately -- logging in is not the
        # client saying where it is.  On `None` the comparison and the label
        # are both exactly what they were before the field existed.
        session = self.session(position=FakePosition(scene_id=2))
        session.client_confirmed_scene = None
        _, err = self.act("/warp 2", session=session)
        said = self.lines(err, self.SAME_SCENE)[0]
        self.assertIn("basis=server_believed_scene ", said)

    def test_a_basis_the_client_never_backed_is_never_claimed(self):
        # Every value that is NOT an honest client-backed scene id must fall
        # back to the weaker word rather than printing the stronger one over
        # a comparison the client had no part in.  `True` is in this list on
        # purpose: `bool` is an `int` subclass and would compare equal to
        # scene 1.
        for value in (True, False, 2.0, "2", object()):
            with self.subTest(value=value):
                session = self.session(position=FakePosition(scene_id=2))
                session.client_confirmed_scene = value
                _, err = self.act("/warp 2", session=session)
                said = self.lines(err, self.SAME_SCENE)[0]
                self.assertIn("basis=server_believed_scene ", said)

    def test_the_basis_decides_a_word_and_never_which_bytes_go_out(self):
        # `same_scene_with_basis` may pick a console sentence and nothing
        # else.  Two connections that differ ONLY in what the client has
        # confirmed must produce byte-identical actions for the same typed
        # line -- otherwise a diagnostic has altered dispatch, which is the
        # one thing this module may never do.
        believed = self.session(position=FakePosition(scene_id=2))
        confirmed = self.session(position=FakePosition(scene_id=2))
        confirmed.client_confirmed_scene = 2
        first, _ = self.act("/warp 2", session=believed)
        second, _ = self.act("/warp 2", session=confirmed)
        self.assertEqual(first[0], second[0])
        self.assertEqual(first[1], second[1])
        self.assertEqual(first[2], second[2])

    def test_this_lane_never_writes_the_clients_own_testimony(self):
        # THE PROPERTY THAT MAKES THE FIELD WORTH MORE THAN
        # `selected.position.scene_id`: it is advanced in `runtime.py` by
        # frames the CLIENT sent and by nothing else.  A GM lane that wrote
        # it would be manufacturing the testimony it then cites -- and a
        # `/warp` is exactly the command that would be tempted to.
        session = self.session(position=FakePosition(scene_id=2))
        session.client_confirmed_scene = 1
        self.act("/warp 5", session=session)
        self.act("/warp 2", session=session)
        self.act("/warp 278", session=session)
        self.assertEqual(session.client_confirmed_scene, 1)

    def test_the_basis_field_name_matches_runtimes_own_constant(self):
        # The attribute name is a literal in `gm/` because importing
        # `runtime` from a `gm/` module would close an import cycle.  A
        # rename on either side must fail loudly here rather than silently
        # falling back to the weaker basis forever.
        import pirateforce_foundation.runtime as runtime

        self.assertEqual(
            runtime.CLIENT_CONFIRMED_SCENE_FIELD,
            chat_command_action.CLIENT_CONFIRMED_SCENE_BASIS_FIELD,
        )

    def test_a_repeat_warp_to_the_scene_the_server_thinks_you_are_in_is_named(self):
        # The retry pf-adversary D2 measured, reproduced at THIS layer: a
        # session whose recorded scene is already the destination -- which is
        # what `runtime.py` leaves behind after one cross-scene warp -- gets
        # the same-scene token, and the `basis=` field is the only thing that
        # tells the tester the word rests on the server's own bookkeeping.
        _, err = self.act("/warp 5", session=self.session(
            position=FakePosition(scene_id=5)
        ))
        said = self.lines(err, self.SAME_SCENE)
        self.assertEqual(len(said), 1, err)
        self.assertIn("basis=server_believed_scene ", said[0])

    def test_the_line_is_ascii(self):
        # The bridge console is cp874; a non-ASCII byte in a token an
        # attended round greps is a line that lane cannot read back.
        _, err = self.act("/warp 2", session=self.session(
            position=FakePosition(scene_id=2)
        ))
        said = self.lines(err, self.SAME_SCENE)[0]
        self.assertEqual(said, said.encode("ascii").decode())


class TheAuditFailurePathTests(_Case):
    """`why` is the word the ndjson CARRIES, not the word the verdict wanted.

    pf-adversary D1, measured: the first version printed the line BEFORE the
    audit write and keyed it on the verdict, so on an unwritable capture
    directory a `/warp 2 100 200` announced `why=withheld_force_pos_vital_
    version` while the audit file held no outcome row at all -- the console
    naming a word the operator cannot find, on the one boot where they are
    reading both.  D2: the branch that DID carry the right word sat behind
    `action is not None`, which cannot happen while both version gates are
    shut, so the reachable case printed the wrong word and the right word
    lived in unreachable code.
    """

    def test_a_no_action_command_whose_audit_failed_says_so(self):
        session = self.session()
        with mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            side_effect=OSError("read-only capture directory"),
        ):
            action, err = self.act("/lv 10", session=session)
        self.assertIsNone(action)
        said = self.lines(err, TOKEN)
        self.assertEqual(len(said), 1, err)
        self.assertIn(
            f"why={chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN} ", said[0]
        )
        # And the word the verdict wanted is NOT on the line, because it is
        # not in the file either.
        self.assertNotIn(chat_command_action.OUTCOME_NO_WIRE_PATH, said[0])

    def test_the_word_on_the_line_is_the_word_in_the_file(self):
        # The other half of the same property: when the row DOES land, the
        # console and the ndjson say the same thing.
        _, err = self.act("/lv 10")
        said = self.lines(err, TOKEN)[0]
        rows = [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        outcomes = [r.get("outcome") for r in rows if r.get("outcome")]
        self.assertEqual(len(outcomes), 1, rows)
        self.assertIn(f"why={outcomes[0]} ", said)

    def test_a_dropped_frame_says_the_audit_row_is_why(self):
        session = self.session()
        with self.open_the_version_gate(), mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            # The real shape of this failure: the capture directory is
            # unwritable, which `_log_outcome` turns into False.  Patched at
            # the writer rather than at `_log_outcome` so the branch under
            # test is reached the way a boot reaches it.
            side_effect=OSError("read-only capture directory"),
        ):
            action, err = self.act("/warp 2 100 200", session=session)
        self.assertIsNone(action, "a frame that cannot be audited is not sent")
        said = self.lines(err, TOKEN)
        self.assertEqual(len(said), 1, err)
        self.assertIn("command=warp ", said[0])
        self.assertIn(
            f"why={chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN} ", said[0]
        )
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_NOT_AUDITED_ACTION_WITHHELD,
            session.events,
        )

    def test_the_audit_word_is_not_an_audit_outcome(self):
        # It names a row that could not be written; putting it in the ndjson
        # vocabulary would invent an outcome no reader will ever find.
        self.assertNotIn(
            chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN,
            gm_commands.AUDIT_OUTCOMES,
        )
        self.assertFalse(
            chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN.startswith(
                gm_commands.AUDIT_OUTCOME_PREFIXES
            )
        )


class TheLineNeverAltersDispatchTests(_Case):
    """A diagnostic may never alter dispatch -- held the same way as the rest."""

    def test_a_none_stderr_is_named_and_costs_no_command(self):
        session = self.session()
        real = sys.stderr
        out = io.StringIO()
        try:
            sys.stderr = None
            with contextlib.redirect_stdout(out):
                action = chat_command_action.make_gm_chat_command_action(
                    session,
                    make_chat_payload("/lv 10"),
                    self.legacy,
                    config_path=str(self.config_path),
                    log_path=str(self.log_path),
                    login_scene_config_path=str(self.login_scene_config_path),
                )
        finally:
            sys.stderr = real
        self.assertIsNone(action)
        # `print(file=None)` writes to STDOUT: the incident this whole family
        # of guards exists to prevent.
        self.assertEqual(out.getvalue(), "")
        self.assertIn(
            f"{chat_command_action.EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr",
            session.events,
        )

    def test_a_stderr_that_raises_is_named_and_costs_no_command(self):
        class Hostile(io.StringIO):
            def write(self, *args, **kwargs):
                raise ValueError("closed stream")

        session = self.session()
        with contextlib.redirect_stderr(Hostile()):
            action = chat_command_action.make_gm_chat_command_action(
                session,
                make_chat_payload("/lv 10"),
                self.legacy,
                config_path=str(self.config_path),
                log_path=str(self.log_path),
                login_scene_config_path=str(self.login_scene_config_path),
            )
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_CONSOLE_WRITE_FAILED_PREFIX}ValueError",
            session.events,
        )
        # The command's own event trail is intact: the console failing is not
        # allowed to look like the route refusing.
        self.assertIn("gm_chat_action_accepted_lv", session.events)

    def test_it_does_not_withhold_an_action_that_was_going_out(self):
        # The backstop runs on the same pass as a SENT command; a mutant
        # that returns early from `_make_action` after printing would take
        # the one command that works away from the tester.
        with self.open_the_version_gate():
            action, err = self.act("/warp 2 100 200")
        self.assertIsNotNone(action)
        self.assertEqual(self.lines(err, TOKEN), [], err)


class TheConsoleEncodingTests(_Case):
    """The bridge console is cp874, and this line is not exempt from that.

    pf-adversary D5: dropping `console_safe` from the three text fields
    survived the whole suite.  The shape it reintroduces is round `qq0i9u`'s
    incident -- a name the console could not encode, and the refusal
    recorded nowhere a person looks.
    """

    class Cp874Stream(io.TextIOWrapper):
        pass

    def _cp874_stream(self):
        buffer = io.BytesIO()
        return io.TextIOWrapper(buffer, encoding="cp874", errors="strict"), buffer

    def test_a_name_the_console_cannot_encode_still_gets_a_line(self):
        stream, buffer = self._cp874_stream()
        session = self.session()
        real = sys.stderr
        try:
            sys.stderr = stream
            chat_command_action._print_no_bytes_way_out(
                session,
                "GM中文",  # CJK: not in cp874
                "lv",
                chat_command_action.OUTCOME_NO_WIRE_PATH,
            )
            stream.flush()
        finally:
            sys.stderr = real
        printed = buffer.getvalue().decode("cp874")
        self.assertIn(chat_command_action.WITHHELD_CONSOLE_TOKEN, printed)
        self.assertEqual(len(printed.strip().splitlines()), 1, printed)
        self.assertNotIn(
            f"{chat_command_action.EVENT_CONSOLE_WRITE_FAILED_PREFIX}"
            "UnicodeEncodeError",
            session.events,
        )

    def test_the_staged_line_is_encoding_safe_too(self):
        stream, buffer = self._cp874_stream()
        session = self.session()
        real = sys.stderr
        try:
            sys.stderr = stream
            chat_command_action._print_staged_way_out(
                session,
                "GM中文",
                gm_commands.GmCommand("warp", ("278",), "/warp 278"),
                chat_command_action.OUTCOME_STAGED_LOGIN_SCENE,
            )
            stream.flush()
        finally:
            sys.stderr = real
        printed = buffer.getvalue().decode("cp874")
        self.assertIn(chat_command_action.STAGED_CONSOLE_TOKEN, printed)
        self.assertIn("scene_id=278 ", printed)


class TheWayOutPrinterReportsHonestlyTests(_Case):
    """`_print_warp_way_out`'s new bool is a claim, so it is pinned.

    pf-adversary D8: flipping either failure return to `True` survived the
    whole suite.  The cost of that lie is the backstop standing down while
    the operator has no line at all.
    """

    def test_a_none_stderr_lets_the_backstop_try_too(self):
        session = self.session()
        real = sys.stderr
        out = io.StringIO()
        try:
            sys.stderr = None
            with contextlib.redirect_stdout(out):
                chat_command_action.make_gm_chat_command_action(
                    session,
                    make_chat_payload("/warp 9999"),
                    self.legacy,
                    config_path=str(self.config_path),
                    log_path=str(self.log_path),
                    login_scene_config_path=str(self.login_scene_config_path),
                )
        finally:
            sys.stderr = real
        self.assertEqual(out.getvalue(), "")
        # Three printers wanted the console on this command: the route line,
        # the scene-list way out, and the backstop the way out's honest
        # `False` let through.  Two would mean the way out claimed a line it
        # never wrote.
        self.assertEqual(
            session.events.count(
                f"{chat_command_action.EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr"
            ),
            3,
            session.events,
        )

    def test_a_raising_stderr_lets_the_backstop_try_too(self):
        class Hostile(io.StringIO):
            def write(self, *args, **kwargs):
                raise ValueError("closed stream")

        session = self.session()
        with contextlib.redirect_stderr(Hostile()):
            chat_command_action.make_gm_chat_command_action(
                session,
                make_chat_payload("/warp 9999"),
                self.legacy,
                config_path=str(self.config_path),
                log_path=str(self.log_path),
                login_scene_config_path=str(self.login_scene_config_path),
            )
        self.assertEqual(
            session.events.count(
                f"{chat_command_action.EVENT_CONSOLE_WRITE_FAILED_PREFIX}ValueError"
            ),
            3,
            session.events,
        )

    def test_the_printer_says_true_only_when_it_wrote(self):
        session = self.session()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            wrote = chat_command_action._print_warp_way_out(
                session, self.GM_ACCOUNT, 9999, login_scene_stage.REASON_UNKNOWN_SCENE
            )
            declined = chat_command_action._print_warp_way_out(
                session,
                self.GM_ACCOUNT,
                278,
                login_scene_stage.REASON_WRITE_FAILED,
            )
        self.assertTrue(wrote)
        self.assertFalse(declined)
        self.assertEqual(len(err.getvalue().strip().splitlines()), 1, err.getvalue())


class TheGuardsOfTheNewPrinterItselfTests(_Case):
    """Measured on the new printer ALONE, not through a command.

    pf-adversary D9: the through-a-command version of this test was green
    because the pre-existing route print had already appended the same event
    for the same session -- deleting the new printer's own guard survived.
    """

    def test_a_none_stderr_is_named_by_this_printer(self):
        session = self.session()
        real = sys.stderr
        out = io.StringIO()
        try:
            sys.stderr = None
            with contextlib.redirect_stdout(out):
                chat_command_action._print_no_bytes_way_out(
                    session,
                    self.GM_ACCOUNT,
                    "lv",
                    chat_command_action.OUTCOME_NO_WIRE_PATH,
                )
        finally:
            sys.stderr = real
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(
            session.events,
            [f"{chat_command_action.EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr"],
        )

    def test_a_none_stderr_is_named_by_the_staged_printer(self):
        session = self.session()
        real = sys.stderr
        out = io.StringIO()
        try:
            sys.stderr = None
            with contextlib.redirect_stdout(out):
                chat_command_action._print_staged_way_out(
                    session,
                    self.GM_ACCOUNT,
                    gm_commands.GmCommand("warp", ("278",), "/warp 278"),
                    chat_command_action.OUTCOME_STAGED_LOGIN_SCENE,
                )
        finally:
            sys.stderr = real
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(
            session.events,
            [f"{chat_command_action.EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr"],
        )

    def test_a_blocker_longer_than_the_cap_is_cut(self):
        # The cap has never executed -- both suppliers are short sentences --
        # so deleting it survived the suite (pf-adversary D11/M1).  The bound
        # belongs to the LINE, not to whichever table filled it in.
        long_one = "x" * (chat_command_action.MAX_CONSOLE_HINT_LENGTH + 50)
        session = self.session()
        err = io.StringIO()
        with mock.patch.dict(
            chat_command_action._NO_BYTES_BLOCKERS_SOURCE,
            {chat_command_action.OUTCOME_NO_WIRE_PATH: long_one},
        ), contextlib.redirect_stderr(err):
            chat_command_action._print_no_bytes_way_out(
                session,
                self.GM_ACCOUNT,
                "lv",
                chat_command_action.OUTCOME_NO_WIRE_PATH,
            )
        printed = err.getvalue()
        self.assertIn("...", printed)
        self.assertNotIn(long_one, printed)
        self.assertIn(
            "x" * chat_command_action.MAX_CONSOLE_HINT_LENGTH + "...", printed
        )


class ContractTests(_Case):
    def test_every_blocker_is_one_ascii_line_within_the_cap(self):
        for why, blocker in chat_command_action.NO_BYTES_BLOCKERS.items():
            with self.subTest(why=why):
                blocker.encode("ascii")
                why.encode("ascii")
                self.assertNotIn("\n", blocker)
                self.assertNotIn("\r", blocker)
                self.assertLessEqual(
                    len(blocker), chat_command_action.MAX_CONSOLE_HINT_LENGTH
                )

    def test_every_named_stage_fault_has_a_blocker_derived_from_upstream(self):
        # pf-adversary D4: the list used to be hand-typed here and said five
        # when there were ten, so a reason added upstream inherited
        # `no blocker recorded` in silence.  Derived now: a sixth
        # NOT_DESTINATION_SHAPED reason turns this red the day it lands.
        for reason in login_scene_stage.NOT_DESTINATION_SHAPED_REASONS:
            with self.subTest(reason=reason):
                outcome = (
                    f"{chat_command_action.OUTCOME_STAGE_REFUSED_PREFIX}{reason}"
                )
                self.assertIn(outcome, chat_command_action.NO_BYTES_BLOCKERS)
        # The destination-shaped ones are NOT here on purpose: they print
        # `GM_CHAT_WARP_REFUSED` with the admissible scene list, and a
        # second sentence would be the doubling this round refuses.
        for reason in login_scene_stage.DESTINATION_SHAPED_REASONS:
            with self.subTest(reason=reason):
                outcome = (
                    f"{chat_command_action.OUTCOME_STAGE_REFUSED_PREFIX}{reason}"
                )
                self.assertNotIn(outcome, chat_command_action.NO_BYTES_BLOCKERS)

    def test_a_stage_fault_names_its_remedy_through_the_dispatcher(self):
        # The one with a one-command fix, measured end to end rather than
        # asserted off the table.
        reason = login_scene_stage.REASON_CONFIG_NOT_WRITABLE
        result = mock.Mock(staged=False, reason=reason, previous_scene_id=None)
        with mock.patch.object(
            login_scene_stage, "stage_login_scene", return_value=result
        ):
            action, err = self.act("/warp 278")
        self.assertIsNone(action)
        said = self.lines(err, TOKEN)
        self.assertEqual(len(said), 1, err)
        self.assertIn("DIRECTORY", said[0])
        self.assertNotIn(chat_command_action.NO_BLOCKER_RECORDED, said[0])

    def test_every_no_bytes_outcome_this_module_can_write_has_a_blocker(self):
        """Every fixed no-bytes word has a sentence -- DERIVED, not hand-typed.

        ~~a hand-typed tuple of nine constants~~ -- STRUCK in round `ntf90h`,
        and the reason is that it failed in exactly the way its own comment
        promised it would not.  It said "a round that adds one more and
        forgets the sentence gets a red test, not a console line reading
        `no blocker recorded`"; round `ntf90h` added
        `OUTCOME_SPEED_ROW_NOT_TOUCHED`, and pf-adversary (D3) measured that
        DELETING its sentence left this file green -- because the list had
        never been extended.  The test one function above this one had
        already been converted to derive-from-upstream for the identical
        defect ("the list used to be hand-typed here and said five when there
        were ten"), which makes this the same hole twice in one file.

        THE RULE, spelled so a reader can check it against the module: a
        constant counts if it is a `str` named `OUTCOME_*` or `WHY_*`, is not
        a prefix (neither the NAME ends `_PREFIX` nor the VALUE ends `_`),
        and its value is a refusal, a withholding, or an audit `WHY_`.  Those
        are exactly the fixed words `_announce_console_outcome` looks up.
        Prefix families are excluded because their suffix is an exception TYPE
        name that cannot be enumerated ahead of time -- those are matched by
        `COMMITTED_ROW_BLOCKER_PREFIXES` instead, which has its own tests.

        Deriving it also turned one PRE-EXISTING gap red and it was fixed in
        the same commit: `/gmprobe`'s `OUTCOME_GMPROBE_UNKNOWN_VARIANT` had no
        sentence, so a GM who typed an unknown variant id read
        `no blocker recorded`.
        """
        derived = []
        for name in sorted(vars(chat_command_action)):
            if not (name.startswith("OUTCOME_") or name.startswith("WHY_")):
                continue
            value = getattr(chat_command_action, name)
            if not isinstance(value, str):
                continue
            if name.endswith("_PREFIX") or value.endswith("_"):
                continue
            if not (
                value.startswith(chat_command_action.OUTCOME_REFUSED_PREFIX)
                or value.startswith(chat_command_action.OUTCOME_WITHHELD_PREFIX)
                or name.startswith("WHY_")
            ):
                continue
            derived.append((name, value))
        # A rule that matched nothing would be green and worthless; the count
        # is a floor, not a pin, so adding a word does not have to touch it.
        self.assertGreaterEqual(len(derived), 9, derived)
        for name, outcome in derived:
            with self.subTest(outcome=name):
                self.assertIn(
                    outcome,
                    chat_command_action.NO_BYTES_BLOCKERS,
                    "%s is a fixed no-bytes word with no operator sentence, "
                    "so its console line reads `no blocker recorded`" % name,
                )

    def test_the_token_is_its_own_grep(self):
        # Three tokens already answer three different questions on this
        # console; a fourth that shares a prefix with one of them would make
        # an operator's grep return the other's lines too.
        for other in (
            chat_command_action.CONSOLE_TOKEN,
            chat_command_action.WARP_REFUSED_CONSOLE_TOKEN,
            chat_command_action.COMMAND_REFUSED_CONSOLE_TOKEN,
        ):
            with self.subTest(other=other):
                self.assertFalse(TOKEN.startswith(other))
                self.assertFalse(other.startswith(TOKEN))

    def test_a_verdict_reports_whether_it_printed(self):
        # The backstop's only input besides the outcome word.  Default False
        # so a handler added later gets the line rather than silence.
        verdict = chat_command_action._Verdict(None, "refused_no_wire_path")
        self.assertFalse(verdict.line_printed)


if __name__ == "__main__":
    unittest.main()
