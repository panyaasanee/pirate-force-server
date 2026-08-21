"""Watch the presentation domain and the chat-input capture at their seams.

The 2026-08-17 owner decision opened the eighth coverage domain
(``presentation``, "Presentation and audio") whole, and the same day's GT-006
attended capture produced the first evidence for ``chat/client_chat_input``:
one undecoded 34-byte vital ``0xAC52`` that the server neither dispatches nor
answers.  Both movements grade rows whose entire substance is *ownership
negatives* — nothing in Foundation produces, handles, or owns any of it yet.

These tests make those negatives fail loudly the day they stop being true, so
the matrix rows cannot silently rot:

  * The chat-input negative stopped being blanket-true on the same day it
    was written: HYP-PF-014 (CHAT-ECHO-001) opened the designed echo lane
    for the unknown chat vital behind the chat input opt-in scenario, graded
    separately in ``chat/chat_input_echo_hypothesis``.  The pin below moved
    from "no module mentions it" to the exact HYP-PF-014 lane files, in the
    same change, exactly as this docstring demanded.  The default mode still
    dispatches nothing and answers nothing (``client_chat_input`` keeps the
    GT-006 grade), and any module beyond the pinned lane mentioning the
    vital still fails loudly here.
  * If a Foundation module starts mentioning music control, the
    ``scene_music_control`` grade moves and the V100 observation stops being
    the row's only evidence.
  * The presentation domain was opened whole — exactly four required rows —
    and per the recorded decision it must not accrete or shrink one row at a
    time without showing up here.
"""

import json
import re
from pathlib import Path

import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
COVERAGE = ROOT / "docs" / "FUNCTIONAL_COVERAGE.json"
PINNED_LEGACY_MODULE = ROOT / "current" / "pf_login_game_server_v141.py"

# The unknown vital captured by GT-006: id 0xAC52 (44114 decimal).  Any of
# these spellings appearing in Foundation source means someone started
# handling it.
UNKNOWN_CHAT_VITAL_PATTERN = r"(?i)AC52|44114"

# The only Foundation modules allowed to mention the unknown chat vital: the
# HYP-PF-014 opt-in echo lane (module + dispatch hookup), plus -- since
# 2026-08-18, chief round 76 -- the HYP-PF-019 channel-message lane.  The
# HYP-PF-014 lane keeps the raw name UNKNOWN_0xAC52, is unreachable without
# --chat-input-hypothesis-scenario, and is graded in
# chat/chat_input_echo_hypothesis; growing this list means a new deliberate
# ownership movement.
#
# The 2026-08-18 movement is exactly that, and it is deliberate: CHAT-CHANNEL-001
# proved 0xAC52 is not an unknown at all but name_id("Channel_LocalTalkMessageVital"),
# one of seventeen ids derivable from the in-image name literals, so
# channel_message_hypothesis.py owns it under its *named* identity as one of the
# five shared-serializer channels.  The id could have been derived from the name
# hash at import time to keep this list at two entries and the scanner green --
# that was deliberately NOT done, because it would leave the repository asserting
# "one module touches 0xAC52" when two do.  The scanner is supposed to notice.
#
# The 2026-08-21 movement (HYP-PF-031, LOGOUT-CHAT-PUSH-001) is likewise
# deliberate: logout_hypothesis.py now names 0xAC52 as its chat-push TRIGGER
# id -- a pinned COPY, never an import (the HYP-PF-027 rule), bound to the
# chat module's own constant by tests/test_logout_chat_push_hypothesis.py --
# because the GT-033 attended trigger is blocked (the tester cannot click the
# HOME menu item, so LogoutVital never arrives) and one accepted ascii12 chat
# frame is the one client action the tester can fire on demand.  The module
# still composes no chat byte and echoes nothing: the classifier reads the
# trigger's nested payload only to accept the ascii12 predicate, no request
# byte is copied into the response or any store, and the only frame the lane
# pushes is the frozen HYP-PF-028 0x709E response.  The id could have been left out of the module by moving the pin
# into runtime.py alone -- that was deliberately NOT done, for the round-76
# reason: it would leave the repository asserting fewer owners than exist.
CHAT_VITAL_ALLOWED_MODULES = [
    "channel_message_hypothesis.py",
    "chat_input_hypothesis.py",
    "logout_hypothesis.py",
    "runtime.py",
]

# MusicControlVital 0x3EAF (16047 decimal), the V100 observation.
MUSIC_CONTROL_PATTERN = r"(?i)MusicControl|3EAF|16047"

# The four rows the presentation domain was opened with, whole, on 2026-08-17.
PRESENTATION_ROWS = (
    "scene_music_control",
    "system_message_display",
    "ui_error_dialog_surfaces",
    "loading_transition_screens",
)


def modules_mentioning(root, pattern):
    found = []
    for path in sorted(Path(root).glob("*.py")):
        if re.search(pattern, path.read_text(encoding="utf-8")):
            found.append(path.name)
    return found


class ChatInputOwnershipTests(unittest.TestCase):
    """Exactly the HYP-PF-014 opt-in lane owns the chat vital, nothing else."""

    def test_no_foundation_module_mentions_the_unknown_chat_vital(self):
        # Until 2026-08-17 this asserted the empty list; HYP-PF-014 moved the
        # pin to its exact opt-in lane in the same change that opened it.
        self.assertEqual(
            modules_mentioning(SRC_ROOT, UNKNOWN_CHAT_VITAL_PATTERN),
            CHAT_VITAL_ALLOWED_MODULES,
        )

    def test_the_scanner_would_notice_a_module_that_started_handling_it(self):
        # Guard the guard: the pattern must actually match the spellings a
        # handler would plausibly use.
        for spelling in ("0xAC52", "0xac52", "AC52", "44114"):
            self.assertRegex(spelling, UNKNOWN_CHAT_VITAL_PATTERN)


class MusicControlOwnershipTests(unittest.TestCase):
    """Music control belongs to the frozen legacy module, not Foundation."""

    def test_no_foundation_module_mentions_music_control(self):
        self.assertEqual(modules_mentioning(SRC_ROOT, MUSIC_CONTROL_PATTERN), [])

    def test_the_frozen_legacy_module_still_carries_music_control(self):
        legacy = PINNED_LEGACY_MODULE.read_text(encoding="utf-8")
        self.assertIn("MusicControlVital", legacy)


class PresentationDomainShapeTests(unittest.TestCase):
    """The domain was opened whole and must change shape only deliberately."""

    def setUp(self):
        document = json.loads(COVERAGE.read_text(encoding="utf-8"))
        matches = [d for d in document["domains"] if d["id"] == "presentation"]
        self.assertEqual(len(matches), 1)
        self.domain = matches[0]

    def test_the_presentation_domain_has_exactly_the_opening_rows(self):
        self.assertEqual(
            tuple(cap["id"] for cap in self.domain["capabilities"]),
            PRESENTATION_ROWS,
        )

    def test_every_presentation_row_stays_required(self):
        for cap in self.domain["capabilities"]:
            self.assertTrue(cap["required"], f"{cap['id']} must stay required")

    def test_no_presentation_row_claims_more_than_in_progress_yet(self):
        # Every current row is an observation of client-side behavior nothing
        # in Foundation owns.  A grade above in_progress requires new runtime
        # evidence plus a report, and has to loosen this pin deliberately.
        for cap in self.domain["capabilities"]:
            self.assertIn(
                cap["status"],
                ("not_started", "in_progress"),
                f"{cap['id']} moved beyond in_progress; re-grade deliberately",
            )


if __name__ == "__main__":
    unittest.main()
