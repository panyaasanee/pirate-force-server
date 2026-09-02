"""The UI-A button stops being a dead click: it answers where she is looking.

WHAT THE PLAYER GETS FROM THIS FILE
-----------------------------------
Today, on a default boot with no scenario flag, clicking the HOME menu's
"back to character select" button (`LogoutVital 0x1B40` subcode 3) produces
NOTHING: no reply frame, no console line, no pixel.  The owner measured
that herself on 2026-09-01 (`pf_bridge/notes_to_chief/consumed/20260901_
1930_KA1A-CAPTURE-*.md`, capture `gt192_20260901_184254`, boot with no
logout scenario at all): the client sent a real 34-byte subcode-3 frame and
the server said nothing back.  Two attended rounds in a row were lost to
that silence (`pf_bridge/NOW.md`, item UI-A).

This module composes the smallest honest answer this project has a codec
for: one `Channel_LocalTalkMessageVital` line carrying exactly twelve ASCII
characters, `BACK REFUSED`, through LANE-GM's already proven composer
(`gm/say_wire.make_local_talk_notice_frame`).  It is the same shape COO
approved for `/speed` refusals (`SPEED DENIED`, COO-DECISION `20260902_
0345`) and for command typos (`TYPO REFUSED`, COO-DECISION `20260902_
0647`): when the server cannot do the thing, it SAYS SO where the player is
looking, rather than dropping the request on the floor.

WHAT THIS FILE DOES NOT CLAIM
-----------------------------
1. It does NOT implement UI-A.  Returning to the character-select screen is
   still unsolved: `GT-033` measured both response policies we own
   (ack+close; `0x709E`+ack+close) leaving the client on the same map for
   50-77 seconds across three attended rounds, and `RE-197` (result
   `20260902_0333`) closed the last candidate pre-click discriminator.  A
   notice is a receipt, not a transition.
2. It does NOT claim the words render.  `gm/say_wire.py`'s own docstring
   states it in capitals and this file repeats it rather than softening it:
   NO SERVER-COMPOSED LINE ON THIS CHANNEL HAS EVER BEEN SEEN ON A SCREEN
   ON A DEFAULT BOOT.  The twelve-character length comes from `GT-006`/
   `GT-009`, where what rendered was the client's OWN echoed text behind a
   scenario flag -- and with the logout dialog closed, which is not the
   state this module fires in.  `GT-205` is the entry that decides it, and
   a negative there is a finding about the dialog and about this channel,
   not proof the composer is wrong.
3. It does NOT send bytes for the UI-B ("exit game", subcode 1) button.
   That path has a live ticket of its own (`GT-194`) whose bytes must not
   change under it, so subcode 1 gets `None` -- pinned by a test.  It DOES
   print one console line for that click, which is itself evidence a
   reader of `GT-194`'s log will see; "nothing" would be the wrong word.
4. It sends nothing and closes nothing.  It composes bytes and hands them
   back, the same posture as `gm/say_wire.py` and `gm/warp_executor.py`.
   The one line that calls it lives in `runtime.py`, which is chief's file
   (CORE-REQUEST in this round's PR body).

ONE ENTRY POINT, ON PURPOSE
---------------------------
`observe_parsed(legacy, parsed)` is the only public way in.  An earlier
draft of this file also exported a raw-bytes path, and pf-adversary
measured what two doors cost: the two accepted DIFFERENT frame sets (the
raw reader accepted `vital_count == 1` plus fifty bytes of junk, which
`logout_hypothesis.classify_logout_attempt` calls `wrong_payload`), and
reported a broken seam under two different tokens.  "chief adds ONE call
site" is only a specification if there is one function with one line
format.  So there is.

WHY THE CLASSIFICATION GOES THROUGH `logout_hypothesis`
-------------------------------------------------------
`classify_logout_attempt` is the function the scenario-gated logout
dispatch itself branches on (`runtime.py:1860`).  Reusing it means this
lane cannot answer a click that dispatch would have called `wrong_payload`.
STATED EXACTLY, because pf-adversary caught the softer version: on a
DEFAULT boot nothing calls that function today (its only call site sits
behind `logout_hypothesis_scenario is not None`), so the call site this
round asks for would be its first production-mode caller.  The claim is
"one reader of these bytes, not two", not "already proven live".

`logout_request_envelope` is imported for its two subcode CONSTANTS only --
same reason: one spelling of `1` and `3` in the tree, not three.

FAIL-CLOSED, STATED AS A PROPERTY, WITH ITS ONE HOLE NAMED
----------------------------------------------------------
Every entry point returns a value rather than raising for every ordinary
input: a malformed parse, an unknown subcode, a `legacy` seam that
misbehaves, a composer that refuses.  The hole, named because
`lane_hooks/__init__.py` names its own: `BaseException` (`KeyboardInterrupt`,
`SystemExit`, `GeneratorExit`) is deliberately NOT caught, here or in
`say_wire`, so a seam that raises one of those still propagates.  That is
Python's own convention for thread targets, not an oversight.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import logout_hypothesis
from . import logout_request_envelope
from .gm import say_wire


# Flag-free by charter: LANE-A ships behaviour that is live on a default
# boot or it does not ship it.  The gate that remains is the standard
# module-level one every lane module is held to.
#
# READ THIS FLAG DIRECTLY, NOT THROUGH `lane_hooks`.
# `lane_hooks.module_production_allowed()` resolves names only under
# `pirateforce_foundation.lane_hooks.` and returns False for everything
# else -- including this module, forever (pf-adversary D7: a call site that
# asked lane_hooks would stand down on every click while `GT-205`'s RECHECK
# reported the wiring present, and the owner would spend a whole attended
# round on it).  `observe_parsed` also checks the flag itself, so a call
# site that forgets still cannot compose bytes.
production_allowed = True

# Twelve ASCII characters, because twelve is the only body length anything
# on this channel has been watched to render (GT-006/GT-009 probe bodies
# `PFCHATPROBE1`/`PFCHATPROBE2`; a five-character body was measured
# SILENT).  The wording follows the house pattern for a visible refusal:
# `SPEED DENIED`, `TYPO REFUSED`, and now `BACK REFUSED` -- "back" being
# the button's own word ("back to character select"), refused because the
# server cannot yet perform it, not because it declined to.
#
# WHAT IS PINNED AND WHAT IS NOT: the LENGTH is measured; the CHARACTER
# CLASS is not.  Both watched bodies were twelve alphanumerics with no
# space, and this text puts a space at index 4 (as `SPEED DENIED` already
# does, so the risk is house-wide, not new here).  Nothing measured covers
# it -- `GT-205` is where that is first exercised.
#
# ~~[assumption of lane A - awaiting COO confirmation; the letter carrying
# it is pf_bridge/notes_to_chief/20260902_0910_LANE-A-ASK-COO-uia-notice-
# wording.md]~~ RULED, round 8z9h9n: COO-DECISION 2026-09-02T09:43+07:00
# (pf_bridge/notes_to_chief/20260902_0943_COO-DECISION-uia-notice-text-
# back-refused-confirmed.md) confirms this exact spelling.  The
# strikethrough-plus-RULED shape is this repo's own (mob_scene_recompose.py
# does the same for a LANE-B assumption): the sweep that hunts for still-
# open lane assumptions greps for the label text, so a retired one has to
# be distinguishable from a live one ON the matched line, not three lines
# further down.
#
# WHAT THE DECISION ACTUALLY SAYS, no wider: it confirms option 1 and
# refuses TWO of the ask letter's four options -- `EXIT REFUSED` (collides
# with the UI-B button) and staying silent (the outcome that burned two of
# the owner's attended rounds).  The letter's option 2, `BACK NOT YET`, is
# NOT adjudicated anywhere: this lane dropped it itself for style, and it
# stays the honest wording for the day the transition becomes performable,
# so a later round should reach for it rather than assume it was refused.
# The one-vocabulary reading (`SPEED DENIED`, `TYPO REFUSED`, `BACK
# REFUSED`) is the REASONING COO gave, not a house rule anyone wrote down;
# it also does not decide REFUSED vs DENIED, and `SPEED DENIED` answers a
# chat command rather than a button, so do not cite this comment as policy.
#
# WHAT IS STILL NOT SETTLED (not a complete list -- see point 2 of this
# module's own docstring for the bigger one): whether a twelve-character
# body with a space at index 4 RENDERS while the logout dialog is open.
# `GT-205` is where a human first sees that -- it accepts the line either
# while the dialog stands or right after it closes -- and a negative result
# there is worth as much as a positive one.
#
# WHAT CHANGING THE SPELLING COSTS, counted rather than guessed: this
# constant, the two test lines that pin the literal, the two prose lines in
# this file that quote it (module docstring and the paragraph above), a new
# COO decision -- and four lines of pf_bridge/GAME_TEST_QUEUE.md's GT-205,
# including the console line a tester copies by hand, which is a
# chief-owned queue file only editable from a cloud clone through a PR.
UIA_NOTICE_TEXT = "BACK REFUSED"

BUTTON_CHARACTER_SELECT = "BACK_TO_CHARSELECT"
BUTTON_EXIT_GAME = "EXIT_GAME"

# ASCII console tokens (the bridge console is cp874; nothing Thai here).
# A human reading a capture log next to a screenshot lines the two up by
# these, which is the wire/DB half of `GT-205`'s two-layer evidence.
#
# `COMPOSED` MEANS BYTES EXIST.  It is emitted only from a
# `LogoutButtonNotice`, i.e. only after `say_wire` returned a frame
# (pf-adversary D2: an earlier draft printed it straight off the
# classification, so a refused composer still logged "COMPOSED").  Every
# other outcome has its own token, so no reader has to guess which of two
# meanings a line carries.
TOKEN_NOTICE_COMPOSED = "LANE_A_UIA_NOTICE_COMPOSED"
TOKEN_NOTICE_FAILED = "LANE_A_UIA_NOTICE_FAILED"
TOKEN_WITHDRAWN = "LANE_A_UIA_WITHDRAWN"
TOKEN_STOOD_DOWN = "LANE_A_UIA_STOOD_DOWN"
TOKEN_UNCLASSIFIED = "LANE_A_LOGOUT_FRAME_UNCLASSIFIED"


@dataclass(frozen=True)
class ButtonClassification:
    """Which of the two HOME-menu buttons a `LogoutVital` frame came from.

    `envelope_vital_count` and `trailing_byte_count` are reported because
    the owner's capture showed the two buttons differing in both, and a
    reader of a console line should be able to tell a lone subcode-3 from a
    bundle without opening the capture file.  They are DESCRIPTION, not the
    discriminator: the code branches on the subcode alone, because the
    capture is n=1 per button and an envelope shape measured once is not a
    rule (the capture letter's own nonclaim says so).
    """

    subcode: int
    button: str
    envelope_vital_count: int
    trailing_byte_count: int

    @property
    def is_character_select(self) -> bool:
        return self.button == BUTTON_CHARACTER_SELECT

    @property
    def is_exit_game(self) -> bool:
        return self.button == BUTTON_EXIT_GAME

    def describe(self) -> str:
        """The fields every console line of this module carries, in order."""

        return "button=%s subcode=%d vitals=%d trailing=%d" % (
            self.button,
            self.subcode,
            self.envelope_vital_count,
            self.trailing_byte_count,
        )

    def console_line(self, token: str) -> str:
        return "%s %s" % (token, self.describe())


@dataclass(frozen=True)
class LogoutButtonNotice:
    """Composed bytes for one on-screen line, plus what they answer.

    `pc` and `frame` are handed back exactly as `gm/say_wire.py` produced
    them; this module never edits a byte of either.
    """

    classification: ButtonClassification
    text: str
    pc: bytes
    frame: bytes

    def console_line(self) -> str:
        return "%s %s text=%s pc=%d frame=%d" % (
            TOKEN_NOTICE_COMPOSED,
            self.classification.describe(),
            self.text,
            len(self.pc),
            len(self.frame),
        )


def _pinned_payload_length(subcode: int) -> int:
    """Length of the LogoutVital payload, read from the module that pins it.

    Not a hand-copied `14`: `classify_logout_attempt` compares the first
    `len(pinned)` bytes, so the trailing count this module reports has to
    follow that same pin or `GT-205`'s `trailing=` field goes quietly wrong
    the day the pin moves (pf-adversary D11).
    """

    return len(logout_hypothesis.LOGOUT_REQUEST_PAYLOADS[subcode])


def classify_parsed(legacy: object, parsed: object) -> ButtonClassification | None:
    """Name the button from the parsed frame `runtime.py` holds, or `None`.

    Never raises for ordinary input; see the module docstring for the
    `BaseException` hole.
    """

    try:
        verdict = logout_hypothesis.classify_logout_attempt(legacy, parsed)
    except Exception:  # noqa: BLE001 - a courtesy must not kill a listener
        return None

    buttons = {
        logout_request_envelope.LOGOUT_SUBCODE_CHARACTER_SELECT: (
            BUTTON_CHARACTER_SELECT
        ),
        logout_request_envelope.LOGOUT_SUBCODE_EXIT_GAME: BUTTON_EXIT_GAME,
    }
    for subcode, button in buttons.items():
        if verdict != "exact_%02d" % (subcode,):
            continue
        try:
            vital_count = int(parsed.vital_count)
            payload_len = len(parsed.nested_payload)
            pinned_len = _pinned_payload_length(subcode)
        except Exception:  # noqa: BLE001 - verdict stands, counters do not
            return None
        return ButtonClassification(
            subcode=subcode,
            button=button,
            envelope_vital_count=vital_count,
            trailing_byte_count=max(0, payload_len - pinned_len),
        )
    return None


def make_uia_notice(
    legacy: object, parsed: object
) -> LogoutButtonNotice | None:
    """Compose the on-screen receipt for the UI-A button, or `None`.

    `None` means "this lane has nothing to send for this click", for every
    reason: an unrecognised frame, the UI-B button, a withdrawn module, or
    a composer that refused.  `observe_parsed` is the entry point that also
    says WHICH.
    """

    if production_allowed is not True:
        return None
    classification = classify_parsed(legacy, parsed)
    if classification is None or not classification.is_character_select:
        return None
    try:
        pc, wire_frame = say_wire.make_local_talk_notice_frame(
            legacy, UIA_NOTICE_TEXT
        )
    except Exception:  # noqa: BLE001 - includes NoticeWireError
        # A courtesy that cannot be composed is dropped, never raised: the
        # same standing rule `gm/chat_command_action.py` applies to the
        # `/speed` refusal notice.
        return None
    return LogoutButtonNotice(
        classification=classification,
        text=UIA_NOTICE_TEXT,
        pc=pc,
        frame=wire_frame,
    )


def observe_parsed(
    legacy: object, parsed: object
) -> tuple[LogoutButtonNotice | None, str]:
    """THE ONE CALL `runtime.py`'s 0x1B40 branch is asked to make.

    Returns `(notice_or_None, console_line)`.  The line is always ASCII and
    always names exactly one of five outcomes, so a click that produces no
    bytes still produces a line an attended tester can line up against a
    screenshot:

    * `LANE_A_UIA_NOTICE_COMPOSED` -- UI-A, and `notice` carries bytes.
    * `LANE_A_UIA_STOOD_DOWN`      -- UI-B, no bytes on purpose.
    * `LANE_A_UIA_WITHDRAWN`       -- UI-A, but this module is switched off.
    * `LANE_A_UIA_NOTICE_FAILED`   -- UI-A, and the composer refused (a bug
                                      to chase, never this lane's decision).
    * `LANE_A_LOGOUT_FRAME_UNCLASSIFIED` -- not a LogoutVital this lane
                                      answers; carries the live classifier's
                                      own verdict word so the reason is in
                                      the log, not guessable from silence.

    The classification is computed ONCE and reused for both halves, so the
    line printed and the bytes returned can never describe two different
    reads of the same object.
    """

    classification = classify_parsed(legacy, parsed)
    if classification is None:
        return None, "%s verdict=%s" % (
            TOKEN_UNCLASSIFIED,
            _safe_verdict(legacy, parsed),
        )

    if not classification.is_character_select:
        return None, classification.console_line(TOKEN_STOOD_DOWN)

    if production_allowed is not True:
        return None, classification.console_line(TOKEN_WITHDRAWN)

    try:
        pc, wire_frame = say_wire.make_local_talk_notice_frame(
            legacy, UIA_NOTICE_TEXT
        )
    except Exception:  # noqa: BLE001 - includes NoticeWireError
        return None, classification.console_line(TOKEN_NOTICE_FAILED)

    composed = LogoutButtonNotice(
        classification=classification,
        text=UIA_NOTICE_TEXT,
        pc=pc,
        frame=wire_frame,
    )
    return composed, composed.console_line()


def _safe_verdict(legacy: object, parsed: object) -> str:
    """The live classifier's own word for this frame, or why there is none.

    A tester diagnosing `GT-205`'s P3 outcome needs to tell "the frame
    never reached this lane" from "it reached it and was rejected", and a
    bare token cannot (pf-adversary D15).  ASCII, single token, no spaces.
    """

    try:
        verdict = logout_hypothesis.classify_logout_attempt(legacy, parsed)
    except Exception as error:  # noqa: BLE001
        return "seam_%s" % (type(error).__name__,)
    if not isinstance(verdict, str) or not verdict.isascii():
        return "nonascii"
    return verdict.replace(" ", "_")
