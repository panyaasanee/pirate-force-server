"""LANE-A's button receipts on the REAL dispatcher, not on the module alone.

Round `1d6rta` widened this file from one button to two: the UI-B ("exit
game") click now composes `EXIT REFUSED` through the same call site, and
the tests that keep `GT-194` measurable -- the two that drive each frame
down the logout-scenario branch -- live here.  The paragraphs below are the
UI-A half as round `od1xso` wrote them.

CORE-REQUEST (LANE-A, ``pf_bridge/notes_to_chief/20260902_0905_LANE-A-CORE-
REQUEST-one-call-site-for-the-uia-button-notice.md``).  The owner's "back to
character select" click (``LogoutVital`` 0x1B40, subcode 3) has been answered
with total silence on every normal boot -- no bytes, and not even a console
line -- and it has cost two whole attended rounds.
``tests/test_world_logout_button_notice.py`` proves the module composes; this
file proves ``runtime.py`` actually CALLS it on the production path and puts
the composed bytes on the wire, which is the only half that was missing and
the half ``GT-205``'s RECHECK reads.

Driven headless through ``make_state_class`` the same way
``tests/test_trace_path_wiring.py`` drives CORE-REQUEST-025, on a boot with
NO logout scenario -- i.e. exactly the boot the owner runs.

WHAT THIS FILE DOES NOT PROVE, and the distinction is the whole point of
``GT-205``:

* Not that anything RENDERS.  This is the wire/DB layer only, and that is
  unchanged by what follows.  ~~No server-composed line on
  ``Channel_LocalTalkMessageVital`` has ever been watched to appear on a
  normal boot (``gm/say_wire.py`` says so itself in capitals).~~  NARROWED,
  round ``kozzu1``: ``GT-205`` came back POSITIVE on 2026-09-02 (R303,
  owner at the keyboard -- ``BACK REFUSED`` on screen), so one such line
  HAS now been watched to appear, on a boot that provably carried no
  LOGOUT scenario.  **A negative ``GT-205`` is worth as much as a positive
  one** -- NOT struck, and it did not become false by being satisfied; it
  is the rule that stops a POSITIVE here from being read as evidence for
  ``GT-211``, which is a different button on a different subcode.
  Three things do not follow from the positive and a reader of this file
  must not take any of them: this file still proves only the wire/DB half
  (the console token was not even copied back off that boot -- "wire/DB:
  not separately instrumented for this ticket"); the boot's argv was never
  recorded, so "flagless" is NOT established, only "no logout scenario";
  and ``gm/say_wire.py`` has not been corrected, so its capitals are stale
  rather than a second source.  The full measurement, and the seven things
  R303 did not settle, are under point 2 of
  ``world_logout_button_notice``'s own docstring.
* Not that UI-A works.  Nothing here makes the client return to character
  select; ``GT-184`` is still open on that question.  This turns "click and
  silence" into "click and a receipt".
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

from pirateforce_foundation import world_logout_button_notice as notice  # noqa: E402
from pirateforce_foundation.gm import say_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    load_chat_input_hypothesis_scenario,
)
from pirateforce_foundation.logout_hypothesis import (  # noqa: E402
    load_logout_hypothesis_scenario,
)
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

NOTICE_ACTION_LABEL = "LANE_A_UIA_BACK_REFUSED_LOCAL_TALK_NOTICE"
NOTICE_COMPOSED_EVENT = "lane_a_uia_back_refused_notice_composed"
OBSERVE_FAILED_PREFIX = "lane_a_uia_notice_observe_failed_"


def _hex(text: str) -> bytes:
    return bytes.fromhex("".join(text.split()))


# The owner's own two captured clicks, transcribed from the fixtures in
# ``tests/test_world_logout_button_notice.py`` -- NOT rebuilt by hand here.
# The guard test below refuses any drift between the two files, so a slip in
# either one cannot leave this file green about the wrong bytes.
UIA_REQUEST_FRAME = _hex(
    """
    12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12
    40 1B 0B 00 08 03 08 00 14 00 00 00 00 14 00 00
    00 00
    """
)

UIB_REQUEST_FRAME = _hex(
    """
    12 6F 6E 14 00 00 00 00 08 00 0B 02 12 04 00 12
    40 1B 0B 00 08 01 08 00 14 00 00 00 00 14 00 00
    00 00 12 B4 1E 0B 00 2A 27 E3 D8 C2 2A 54 19 97
    46 2A DF 29 F5 C5 2A 00 80 F3 43 0F 01 00 12 B4
    1E 0B 00 2A 8B 70 FA C2 2A A1 90 96 46 2A 4B 95
    FC C5 2A 00 00 F2 43 0F 01 00 12 90 2A 0B 00 2A
    34 80 96 46 2A 86 79 FD C5 2A 00 00 F2 43 2A 9F
    5C DC 3F 0B 01 0B 00
    """
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class TheFixturesMatchLaneAsOwnTests(unittest.TestCase):
    """The two frames here are the two frames the module's tests pin.

    Copied bytes rot.  This test is why a copy is acceptable at all: it
    fails the moment the two files stop describing the owner's same clicks.
    """

    def test_both_frames_are_byte_identical_to_the_module_test_fixtures(self):
        module_tests = ROOT / "tests" / "test_world_logout_button_notice.py"
        source = module_tests.read_text(encoding="utf-8")
        namespace: dict = {}
        # Re-run only the two hex literals, not the whole module: the file
        # imports the runtime and building it twice is slow and pointless.
        for name in ("UIA_REQUEST_FRAME", "UIB_REQUEST_FRAME"):
            start = source.index("%s = _hex(" % name)
            body = source[source.index('"""', start) + 3:]
            namespace[name] = _hex(body[:body.index('"""')])
        self.assertEqual(namespace["UIA_REQUEST_FRAME"], UIA_REQUEST_FRAME)
        self.assertEqual(namespace["UIB_REQUEST_FRAME"], UIB_REQUEST_FRAME)


class UiaNoticeWiringTests(unittest.TestCase):
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

    def _state_type(self):
        return make_state_class(self.legacy, self.lifecycle, self.projector)

    def _logged_in_state(self, token):
        legacy = self.legacy
        state = self._state_type()(token)
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(character.selector)
        ))
        return state

    def _click(self, token, frame):
        """Dispatch one click, returning (actions, printed console text)."""
        state = self._logged_in_state(token)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            actions = state.dispatch(self.legacy.parse_outer(frame))
        return state, actions, buffer.getvalue()

    def _scenario_click(self, token, frame):
        """The same click, but on a boot that loaded a logout scenario.

        Extracted in round `1d6rta` so both buttons can be driven down the
        scenario branch by the two tests that keep `GT-194` measurable --
        copying the body a second time is how the two copies drift.
        """

        scenario = load_logout_hypothesis_scenario(
            ROOT / "scenarios" / "logout_hypothesis_ack_close.json"
        )
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            logout_hypothesis_scenario=scenario,
        )
        state = state_type(token)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_client_login_pc(token)
            ))
            state.dispatch(self.legacy.parse_outer(
                self.legacy._V25_REAL_CREATE_PC
            ))
            character = self.store.list_characters(
                state.foundation.account_id
            )[-1]
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)
            ))
            buffer.truncate(0)
            buffer.seek(0)
            actions = state.dispatch(self.legacy.parse_outer(frame))
        return state, actions, buffer.getvalue()

    def _notice_actions(self, actions):
        return [a for a in actions if a[0] == NOTICE_ACTION_LABEL]

    # ---- the receipt itself -------------------------------------------

    def test_the_uia_click_puts_exactly_one_notice_on_the_wire(self):
        state, actions, _out = self._click("uia_wire", UIA_REQUEST_FRAME)
        composed = self._notice_actions(actions)
        self.assertEqual(len(composed), 1, actions)
        label, pc, frame, delay = composed[0]
        self.assertEqual(label, NOTICE_ACTION_LABEL)
        self.assertEqual(delay, 0.0)
        self.assertIn(NOTICE_COMPOSED_EVENT, state.events)
        expected_pc, expected_frame = say_wire.make_local_talk_notice_frame(
            self.legacy, notice.UIA_NOTICE_TEXT,
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_the_body_on_the_wire_is_the_twelve_ascii_characters(self):
        # The length is what GT-006/GT-009 measured; the wording is lane A's
        # stated assumption.  Both are pinned here so a silent edit to either
        # is a red test and not a surprise on the owner's screen.
        self.assertEqual(notice.UIA_NOTICE_TEXT, "BACK REFUSED")
        self.assertEqual(len(notice.UIA_NOTICE_TEXT), 12)
        _state, actions, _out = self._click("uia_body", UIA_REQUEST_FRAME)
        _label, pc, _frame, _delay = self._notice_actions(actions)[0]
        # The channel carries UTF-16LE, not bytes -- measured here, not
        # assumed: a test that looked for the plain ASCII run would pass on
        # an empty body just as happily.
        self.assertIn("BACK REFUSED".encode("utf-16-le"), pc)

    def test_the_notice_rides_last_and_claims_nothing_ahead_of_the_frame(self):
        _state, actions, _out = self._click("uia_last", UIA_REQUEST_FRAME)
        # pf-adversary N2: asserting `actions[-1]` alone is satisfied by a
        # list of length one, which is what a `return uia_notice_actions`
        # inserted at the composition site produces -- and that mutant
        # swallows the frame's own inherited replies while leaving this file
        # green.  So pin that the frame's own actions are STILL THERE and
        # still ahead, not just that the receipt is at the end.
        self.assertEqual(actions[-1][0], NOTICE_ACTION_LABEL)
        self.assertGreater(
            len(actions), 1,
            "the click's own inherited replies were swallowed",
        )
        self.assertEqual(
            [a[0] for a in actions].count(NOTICE_ACTION_LABEL), 1,
        )

    def test_a_scenario_boot_composes_nothing_and_never_says_composed(self):
        # pf-adversary D1, MEASURED: the first draft printed the
        # byte-identical `LANE_A_UIA_NOTICE_COMPOSED ... pc=56 frame=66` line
        # on a logout-scenario boot, where the branch below early-returns and
        # the receipt never leaves the process.  A tester lining the console
        # up against a screenshot would read "composed, and nothing
        # rendered" and record a FALSE NEGATIVE GT-205 -- whose negative is
        # declared to be worth as much as its positive.
        #
        # This also closes the mutant that survived the whole suite:
        # narrowing the branch to `logout_hypothesis_scenario is None` used
        # to leave 7185 tests green, because every other test boots flagless.
        state, actions, out = self._scenario_click(
            "uia_scenario", UIA_REQUEST_FRAME
        )
        self.assertEqual(self._notice_actions(actions), [])
        self.assertNotIn(NOTICE_COMPOSED_EVENT, state.events)
        self.assertNotIn(notice.TOKEN_NOTICE_COMPOSED, out)
        self.assertIn("LANE_A_UIA_NOTICE_NOT_THIS_BOOT", out)
        self.assertIn("lane_a_uia_notice_scenario_owns_frame", state.events)
        out.encode("ascii")

    def test_a_scenario_boot_composes_nothing_for_the_uib_click(self):
        # THIS IS THE GUARD THAT KEEPS `GT-194` MEASURABLE.  That entry
        # boots a logout scenario and grades on `_dispatch_logout_hypothesis`
        # answering the owner's 119-byte frame; round `1d6rta` gave the same
        # frame a receipt on DEFAULT boots.  The two only stay separable if
        # the scenario branch owns the frame outright -- so this drives the
        # UI-B frame down the scenario branch and pins that not one byte of
        # this lane's is composed there.
        state, actions, out = self._scenario_click(
            "uib_scenario", UIB_REQUEST_FRAME
        )
        self.assertEqual(self._notice_actions(actions), [])
        self.assertNotIn(NOTICE_COMPOSED_EVENT, state.events)
        self.assertNotIn(notice.TOKEN_NOTICE_COMPOSED, out)
        self.assertNotIn("EXIT REFUSED", out)
        self.assertIn("LANE_A_UIA_NOTICE_NOT_THIS_BOOT", out)
        self.assertIn("lane_a_uia_notice_scenario_owns_frame", state.events)
        out.encode("ascii")

    # ---- the console line, which is the tester's other half ------------

    def test_the_uia_click_prints_the_composed_line_and_it_is_ascii(self):
        _state, _actions, out = self._click("uia_line", UIA_REQUEST_FRAME)
        self.assertIn(notice.TOKEN_NOTICE_COMPOSED, out)
        out.encode("ascii")  # raises if the bridge console could not print it

    def test_the_uib_click_puts_its_own_notice_on_the_wire(self):
        # ~~UI-B (exit game) stands down ON PURPOSE so GT-194's evidence
        # cannot move under the owner's feet.~~  SUPERSEDED, round
        # `1d6rta` (COO-DECISION `20260902_1145`): UI-B is this lane's
        # work now, and GT-194's evidence still cannot move because that
        # ticket boots a logout scenario, where this call site composes
        # nothing at all (pinned by
        # `test_a_scenario_boot_composes_nothing_and_never_says_composed`
        # and by `test_a_scenario_boot_composes_nothing_for_the_uib_click`
        # below, which drives THIS frame down that branch).
        #
        # No new chief-owned line was needed for any of this: the call
        # site sends whatever `observe_parsed` returns, so this test is
        # the proof that the existing wiring carries the second button.
        state, actions, out = self._click("uib", UIB_REQUEST_FRAME)
        composed = self._notice_actions(actions)
        self.assertEqual(len(composed), 1, actions)
        _label, pc, frame, delay = composed[0]
        self.assertEqual(delay, 0.0)
        self.assertIn(NOTICE_COMPOSED_EVENT, state.events)
        expected_pc, expected_frame = say_wire.make_local_talk_notice_frame(
            self.legacy, notice.UIB_NOTICE_TEXT,
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertIn("EXIT REFUSED".encode("utf-16-le"), pc)
        self.assertIn(notice.TOKEN_NOTICE_COMPOSED, out)
        self.assertIn("button=EXIT_GAME", out)
        self.assertNotIn(notice.TOKEN_STOOD_DOWN, out)
        out.encode("ascii")

    def test_the_uib_notice_rides_last_and_swallows_nothing(self):
        # The mutant this closes is the same one pf-adversary N2 closed for
        # UI-A: a `return` at the composition site would hand back only the
        # receipt and drop the frame's own inherited replies, with every
        # other assertion in this file still green.
        #
        # WHAT IT COVERS AND WHAT IT DOES NOT, stated because the first
        # version of this comment overclaimed (pf-adversary D6, MEASURED):
        # the three companion actions exist here only because this click is
        # the SESSION'S FIRST runtime request, so it carries the handshake.
        # On the owner's real click -- and in the state `GT-194` demands,
        # after walking or fighting -- the list is exactly `[notice]`, and
        # in THAT state this assertion cannot tell the mutant apart.  The
        # coverage is real but it is first-request coverage; nothing here
        # proves the second click keeps its inherited replies, because on
        # the second click there are none to keep.
        _state, actions, _out = self._click("uib_last", UIB_REQUEST_FRAME)
        self.assertEqual(actions[-1][0], NOTICE_ACTION_LABEL)
        self.assertGreater(
            len(actions), 1,
            "the click's own inherited replies were swallowed",
        )
        self.assertEqual(
            [a[0] for a in actions].count(NOTICE_ACTION_LABEL), 1,
        )

    def test_a_repeated_click_still_answers_and_answers_only_once(self):
        # The state the owner and `GT-194` are actually in: the click is
        # NOT the session's first runtime request.  Measured here rather
        # than assumed (pf-adversary D6): the handshake companions are
        # gone, the receipt is still composed, and there is exactly one of
        # it per click -- this lane does not batch, dedupe or rate-limit,
        # and a player who clicks a still-dead button ten times gets ten
        # 66-byte frames.  That is stated as the shipped behaviour, not
        # defended as a good one; the fix, if it is ever wanted, belongs at
        # the call site in chief's file, not here.
        state = self._logged_in_state("uib_repeat")
        seen = []
        for _ in range(3):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                actions = state.dispatch(
                    self.legacy.parse_outer(UIB_REQUEST_FRAME)
                )
            seen.append([a[0] for a in actions])
            self.assertEqual(len(self._notice_actions(actions)), 1, actions)
            self.assertIn(notice.TOKEN_NOTICE_COMPOSED, buffer.getvalue())
        # The later clicks carry nothing but the receipt, which is exactly
        # why the assertion in the test above is first-request-only.
        self.assertEqual(seen[1], [NOTICE_ACTION_LABEL], seen)
        self.assertEqual(seen[2], [NOTICE_ACTION_LABEL], seen)

    def test_a_non_logout_scenario_boot_still_composes_the_receipt(self):
        # MEASURED, and it contradicts the sentence this lane first wrote
        # (pf-adversary D4): the call site's guard names the LOGOUT
        # scenario, not "any scenario", so a boot carrying one of the other
        # scenario keywords composes this notice like a flagless boot does.
        # Pinned so the next reader learns it from a test instead of from a
        # surprised tester: `GT-211` asks for a flagless boot, but a ticket
        # that boots some OTHER scenario and clicks this button WILL see
        # the frame, and that is not a defect, it is the shape.
        # A real boot with a real non-logout scenario object, not a source
        # read: the chat-echo scenario is the cheapest one to load, and any
        # of the other twenty-seven keywords would behave the same.
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            chat_input_hypothesis_scenario=(
                load_chat_input_hypothesis_scenario(
                    ROOT / "scenarios" / "chat_input_hypothesis_echo.json"
                )
            ),
        )
        state = state_type("uib_nonlogout")
        legacy = self.legacy
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_client_login_pc("uib_nonlogout")
            ))
            state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
            character = self.store.list_characters(
                state.foundation.account_id
            )[-1]
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_start_game_pc(character.selector)
            ))
            buffer.truncate(0)
            buffer.seek(0)
            actions = state.dispatch(legacy.parse_outer(UIB_REQUEST_FRAME))
        out = buffer.getvalue()
        self.assertEqual(len(self._notice_actions(actions)), 1, actions)
        self.assertIn(notice.TOKEN_NOTICE_COMPOSED, out)
        self.assertIn("button=EXIT_GAME", out)
        self.assertNotIn("LANE_A_UIA_NOTICE_NOT_THIS_BOOT", out)
        # And the guard really is the logout one, so this behaviour follows
        # from the branch rather than from this fixture's luck.
        code = (ROOT / "src/pirateforce_foundation/runtime.py").read_text(
            encoding="utf-8"
        )
        head = code[:code.index("world_logout_button_notice.observe_parsed")]
        guard = head[head.rindex("elif ("):]
        self.assertIn("logout_hypothesis_scenario is not None", guard)

    def test_the_two_buttons_reach_the_wire_with_different_bytes(self):
        # End to end, through the real dispatch, not through the composer:
        # what leaves the server for one click is not what leaves it for
        # the other.  A table lookup that silently fell back to UI-A's
        # sentence would pass every per-button test above and fail here.
        _a_state, a_actions, _a_out = self._click("both_a", UIA_REQUEST_FRAME)
        _b_state, b_actions, _b_out = self._click("both_b", UIB_REQUEST_FRAME)
        a_pc = self._notice_actions(a_actions)[0][1]
        b_pc = self._notice_actions(b_actions)[0][1]
        self.assertNotEqual(a_pc, b_pc)

    def test_a_frame_that_is_not_a_logout_vital_is_not_observed_at_all(self):
        # The GetWorldInfo poll the client sends constantly.  If this branch
        # ever widened past 0x1B40 it would print on every frame and drown
        # the console the attended tester reads.
        legacy = self.legacy
        poll = (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 0)
            + legacy.u8tag(0x0B, 0)
        )
        _state, actions, out = self._click("not_logout", poll)
        self.assertEqual(self._notice_actions(actions), [])
        self.assertNotIn(notice.TOKEN_NOTICE_COMPOSED, out)
        self.assertNotIn(notice.TOKEN_UNCLASSIFIED, out)

    # ---- fail-closed ---------------------------------------------------

    def test_a_connection_with_no_character_selected_gets_no_bytes(self):
        # MEASURED before the guard existed: a session that had never logged
        # in at all still got a composed Channel_LocalTalkMessageVital back
        # for one 0x1B40 frame.  Nobody can click an in-game menu button
        # before they are in the game, so the only caller that reaches this
        # is a client sending the frame on its own -- and an unauthenticated
        # connection must not be able to make this server compose bytes.
        # Same answer `trace_path` gives the identical situation one branch
        # above: empty list, named event.
        state = self._state_type()("uia_no_login")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            actions = state.dispatch(self.legacy.parse_outer(UIA_REQUEST_FRAME))
        self.assertEqual(self._notice_actions(actions), [])
        self.assertNotIn(NOTICE_COMPOSED_EVENT, state.events)
        self.assertIn("lane_a_uia_notice_no_selected_no_reply", state.events)

    def test_a_withdrawn_module_sends_nothing_and_says_so(self):
        original = notice.production_allowed
        notice.production_allowed = False
        try:
            state, actions, out = self._click("withdrawn", UIA_REQUEST_FRAME)
        finally:
            notice.production_allowed = original
        self.assertEqual(self._notice_actions(actions), [])
        self.assertNotIn(NOTICE_COMPOSED_EVENT, state.events)
        self.assertIn(notice.TOKEN_WITHDRAWN, out)

    def test_an_observer_that_raises_is_named_and_does_not_reach_the_thread(self):
        # `observe_parsed` promises not to raise for ordinary input, but a
        # courtesy line must never be the reason a player's connection dies,
        # so the call site catches anyway -- and the catch has to be proven,
        # not asserted in a comment.
        def _explode(*args, **kwargs):
            raise RuntimeError("observer blew up")

        original = notice.observe_parsed
        notice.observe_parsed = _explode
        try:
            state, actions, _out = self._click("raises", UIA_REQUEST_FRAME)
        finally:
            notice.observe_parsed = original
        self.assertEqual(self._notice_actions(actions), [])
        self.assertIn(
            OBSERVE_FAILED_PREFIX + "RuntimeError", state.events,
        )

    def test_the_call_site_does_not_ask_the_lane_hooks_gate(self):
        # `lane_hooks.module_production_allowed()` resolves names only under
        # `pirateforce_foundation.lane_hooks.` and answers False for this
        # module forever.  A call site that asked it would stand down on
        # every click while GT-205's RECHECK reported the wiring present --
        # the exact way to burn another attended round (letter's D7).
        source = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        start = source.index("def _dispatch_with_lanes(self, parsed):")
        # Up to the call itself, not a fixed byte window: the window version
        # broke the moment the block grew a branch, which is a test that
        # fails for a reason that has nothing to do with what it checks.
        block = source[start:source.index(
            "world_logout_button_notice.observe_parsed", start,
        ) + len("world_logout_button_notice.observe_parsed")]
        self.assertIn("world_logout_button_notice.observe_parsed", block)
        # CODE only.  The call site's own comment names the trap it is
        # avoiding, and a check that read comments too would forbid writing
        # that warning down -- which is the one place a future round will
        # look before repeating it.
        code = "\n".join(
            line for line in block.splitlines()
            if not line.lstrip().startswith("#")
        )
        head = code[:code.index("world_logout_button_notice.observe_parsed")]
        self.assertNotIn("module_production_allowed", head)


if __name__ == "__main__":
    unittest.main()
