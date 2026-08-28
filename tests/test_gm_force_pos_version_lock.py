"""The ForcePos version switch stays off until the write point that pairs with it exists.

WHY THIS FILE EXISTS (a rule that was held by a sentence, twice, and lost)
--------------------------------------------------------------------------
RE-129 answered on 2026-08-28T20:09+07:00: the `ForcePos` (0x0E80) vital
version byte is 0, read straight out of the prototype constructor
(`mov byte ptr [eax+0x10],cl` after `xor ecx,ecx`, 0x005E5186) and compared by
the generic reader with exact equality (0x005F3EFC). That is the answer this
lane had been blocked on for two days, and the obvious next move -- set
`teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED = 0` and let warps fly -- is
exactly the move COO forbade three hours later.

COO-DECISION 2026-08-28T21:30+07:00 (pf_bridge/notes_to_chief/
20260828_2130_COO-DECISION-position-ownership-after-gm-warp.md) ruled that the
owner of a character's position is the position the CLIENT confirmed, that the
server must never write a position it did not observe, and that the confirming
event is the first `TargetPos` after the frame. It then put a hard lock on this
lane in one line: do not change `FORCE_POS_VITAL_VERSION_CONFIRMED` from None
until that confirmed write point is on `main` -- EVEN THOUGH RE-129 already
answered.

The reason that lock needs a test rather than a comment is this lane's own
recent record. Round `gr2q9j` wrote "wire exactly one of the two" into a letter
and a docstring; chief wired the other one the same evening, in good faith,
because a sentence in a letter is not a check. Round `vvxkft` replaced that
sentence with `OneOfTwoWiringTests`, which reads `runtime.py` and refuses the
double-wired state. This file is the same move for the same class of mistake:
the next round to read "RE-129 = 0" in the source will be tempted, and the only
thing that should stop it is a red test naming the missing precondition.

WHAT IT ENFORCES (one direction, deliberately)
-----------------------------------------------
If `FORCE_POS_VITAL_VERSION_CONFIRMED` is not None, then `runtime.py` must
contain the confirmed-position write point -- identified by the console/label
token `GM_WARP_POSITION_CONFIRMED`, which CORE-REQUEST-GM-030 asks chief to
place at that write site precisely so this test has something exact to grep.

The other direction is NOT enforced, on purpose: when chief lands the write
point, the constant is still allowed to be None. Lifting the lock is COO's
call, not a mechanical consequence of a grep -- and a test that went red inside
chief's own pull request, for a lane he does not own, would be a red he cannot
fix and would teach everyone here to ignore this file.

WHAT IT DOES NOT CLAIM
----------------------
Nothing here says a version-correct ForcePos frame will move a character. RE-129
also measured that the handler the client has REGISTERED for ForcePos is the
complete body [0x00710440,0x00710445) = `mov al,1; ret 4`: no payload read, no
position write. The version byte was necessary, not sufficient, and GT-128
remains the only thing that can decide the on-screen half.
"""
from __future__ import annotations

import inspect
import pathlib
import subprocess
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pirateforce_foundation.gm import teleport_wire, warp_executor  # noqa: E402

# The token CORE-REQUEST-GM-030 asks chief to put at the confirmed write site
# in runtime.py, in the same screaming-snake ASCII style as every other console
# token in this lane (LANE_GM_CHAT_ACTION, GM_UPDATE_STATE_AFTER_LOGIN). It is
# a literal here so that renaming it on either side goes red rather than silent.
CONFIRMED_WRITE_POINT_TOKEN = "GM_WARP_POSITION_CONFIRMED"

RUNTIME_PY = REPO_ROOT / "src" / "pirateforce_foundation" / "runtime.py"

# The two names that record RE-129's measurement without acting on it. They may
# appear in their own definition block and nowhere else in the lane's shipped
# sources: a record is not a switch.
RECORD_NAMES = (
    "FORCE_POS_VITAL_VERSION_PROVEN_BY_RE129",
    "TELEPORT_VITAL_VERSION_PROVEN_BY_RE129",
)
RECORD_HOME = "src/pirateforce_foundation/gm/teleport_wire.py"

LANE_PATH_SPECS = (
    "src/pirateforce_foundation/gm",
    "src/pirateforce_foundation/lane_hooks/lane_gm_*.py",
)


def _tracked_lane_files() -> list[str] | None:
    """Repo-relative paths of the lane's tracked .py files, or None if no git."""
    done = subprocess.run(
        ("git", "ls-files", "-z", "--", *LANE_PATH_SPECS),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
    )
    if done.returncode != 0:
        return None
    return sorted(p for p in done.stdout.split("\0") if p.endswith(".py"))


class ForcePosVersionLockTests(unittest.TestCase):
    def test_the_switch_may_only_be_on_when_runtime_has_the_write_point(self):
        confirmed = teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED
        if confirmed is None:
            return
        self.assertTrue(
            RUNTIME_PY.is_file(),
            "FORCE_POS_VITAL_VERSION_CONFIRMED is set but runtime.py could not "
            "be read to check its precondition: %s" % RUNTIME_PY,
        )
        source = RUNTIME_PY.read_text(encoding="utf-8", errors="surrogateescape")
        self.assertIn(
            CONFIRMED_WRITE_POINT_TOKEN,
            source,
            "FORCE_POS_VITAL_VERSION_CONFIRMED was changed from None to %r, but "
            "runtime.py contains no %s -- the confirmed-position write point "
            "(CORE-REQUEST-GM-030) is not on main. COO-DECISION "
            "2026-08-28T21:30+07:00 locks this constant at None until it is: a "
            "ForcePos frame is a request, and the server must never write a "
            "position it did not observe. Sending warps now means the client "
            "stands at the new point while the durable row keeps the old one, "
            "and aggro range, pickup range and the logout point all follow the "
            "row. Revert the constant, or land the write point first."
            % (confirmed, CONFIRMED_WRITE_POINT_TOKEN),
        )

    def test_the_recorded_re129_values_are_what_the_result_letter_says(self):
        # Provenance for both: notes_to_chief/20260828_2009_RE-129-RESULT-
        # VERSION-ZERO-HANDLER-NOOP.md, T1 (ForcePos constructor writes 0 at
        # 0x005E5186) and T3 (TeleportVital constructor writes 4 at 0x005E5425).
        self.assertEqual(teleport_wire.FORCE_POS_VITAL_VERSION_PROVEN_BY_RE129, 0)
        self.assertEqual(teleport_wire.TELEPORT_VITAL_VERSION_PROVEN_BY_RE129, 4)

    def test_the_two_recorded_values_are_different_measurements(self):
        # Guards the one-line mistake that would make the pair meaningless: if
        # both ever read the same value, the "there is no project-wide default"
        # argument that keeps every send gated stops being demonstrated by them.
        self.assertNotEqual(
            teleport_wire.FORCE_POS_VITAL_VERSION_PROVEN_BY_RE129,
            teleport_wire.TELEPORT_VITAL_VERSION_PROVEN_BY_RE129,
        )

    def test_the_records_are_inert_across_the_lane(self):
        tracked = _tracked_lane_files()
        if tracked is None:
            self.skipTest("git is not available; the inertness grep needs it")
        self.assertGreater(len(tracked), 5, tracked)
        self.assertIn(RECORD_HOME, tracked)
        for name in RECORD_NAMES:
            for rel in tracked:
                if rel == RECORD_HOME:
                    continue
                text = (REPO_ROOT / rel).read_text(
                    encoding="utf-8", errors="surrogateescape"
                )
                self.assertNotIn(
                    name,
                    text,
                    "%s mentions %s. That name is a RECORD of what RE-129 "
                    "measured, not a switch: the only constant a send may gate "
                    "on is FORCE_POS_VITAL_VERSION_CONFIRMED, which COO has "
                    "locked at None. Using the record to build or gate a frame "
                    "routes around the lock without changing the locked line."
                    % (rel, name),
                )

    def test_no_force_pos_builder_defaults_its_version(self):
        # The lock is worth nothing if a builder quietly supplies a version of
        # its own when the caller omits one. Every ForcePos/Teleport frame
        # builder must force the caller to say the byte out loud.
        for func in (
            teleport_wire.make_force_pos_frame,
            teleport_wire.make_teleport_vital_frame,
            teleport_wire.make_cwarp_result_frame,
            warp_executor.make_warp_force_pos_frame,
        ):
            parameter = inspect.signature(func).parameters.get("vital_version")
            self.assertIsNotNone(
                parameter, "%s lost its vital_version parameter" % func.__name__
            )
            self.assertIs(
                parameter.default,
                inspect.Parameter.empty,
                "%s gained a default vital_version. A default is a guess with a "
                "polite name: GT-101 measured what an unproven version does to a "
                "real client (modal error, connection halted, socket closed)."
                % func.__name__,
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
