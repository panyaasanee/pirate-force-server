"""LEARN-SKILL-REQUEST-001: the arming proof that decides whether the
attended ticket boards the capture bus.

NOW.md (PANYA 0159) has ka1-A re-run the ticket's ``HEADLESS_PROOF:`` command
before an attended boot and CULL the ticket when it does not reproduce.  So
these guards stand between the runner and a wasted boot on Panya's machine:
the documented command must work on a plain checkout, the token must say what
the run actually did, and a token produced by another checkout's modules must
be impossible.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    learn_skill_request_hypothesis as R,
)
from pirateforce_foundation import (  # noqa: E402
    skill_learn_request_headless as H,
)


def _plain_env(tmp_path):
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("PYTHONPATH", "PYTHONHOME")
    }
    env["TMPDIR"] = str(tmp_path)
    return env


def test_the_proof_points_at_the_committed_opt_in_scenario():
    assert H.SCENARIO_PATH.is_file(), H.SCENARIO_PATH
    scenario = R.load_learn_skill_request_hypothesis_scenario(H.SCENARIO_PATH)
    assert scenario.scenario_id == R.LEARN_SKILL_REQUEST_SCENARIO_ID
    assert R.production_allowed is False


def test_the_lane_event_filter_can_never_hide_the_events_it_checks():
    # _drive() keeps only events with the lane prefix, because other lanes
    # narrate the same frame.  If either event under test stopped matching
    # that prefix, every assertion in the proof would pass vacuously against
    # an empty list -- so pin the relationship, not just the strings.
    assert H.DECODED_EVENT.startswith(H.LANE_EVENT_PREFIX)
    assert H.REFUSED_EVENT.startswith(H.LANE_EVENT_PREFIX)
    assert H.DECODED_EVENT != H.REFUSED_EVENT


@pytest.mark.parametrize("label", R.LEARN_SKILL_REQUEST_PROBE_ORDER)
def test_each_pinned_probe_is_decoded_recorded_and_answered_with_nothing(
    label,
):
    fields = R.LEARN_SKILL_REQUEST_PROBE_FIELDS[label]
    line = H.prove_one_probe(label)
    assert line.isascii()
    assert line.startswith(
        H.TOKEN_PREFIX + " case=probe_" + label + " actions=0 "
    )
    assert "event=" + H.DECODED_EVENT in line
    assert "u32=%d" % fields.request_u32_0x14 in line
    assert "u8=%d" % fields.request_u8_0x18 in line
    assert "db_unchanged=yes" in line


def test_the_real_captured_frame_is_refused_and_the_token_says_so():
    # The measured state of the lane today: ka1-A's own frame #70 carries the
    # 0x36AA vital as the first of TWO nested vitals, and this lane accepts
    # one.  A token claiming acceptance here would be a token nobody could
    # reproduce at the game client, so the proof asserts the REFUSAL.
    line = H.prove_the_real_capture()
    assert line.isascii()
    assert line.startswith(
        H.TOKEN_PREFIX + " case=real_r312_frame70 actions=0"
    )
    assert "event=" + H.REFUSED_EVENT in line
    assert "vitals=2" in line
    assert "second_vital=0x0F01" in line
    assert R.LEARN_SKILL_REQUEST_REAL_CAPTURE_VITAL_COUNT == 2


def test_the_documented_single_case_command_runs_on_a_plain_checkout(
    tmp_path,
):
    done = subprocess.run(
        [
            sys.executable,
            "src/pirateforce_foundation/skill_learn_request_headless.py",
            "--real",
        ],
        cwd=str(ROOT), env=_plain_env(tmp_path),
        capture_output=True, text=True, timeout=600,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    assert (
        H.TOKEN_PREFIX + " case=real_r312_frame70 actions=0" in done.stdout
    ), done.stdout[-2000:]


def test_the_whole_documented_command_prints_the_summary_token(tmp_path):
    """The argument-less form is the one whose line goes into the ticket."""
    done = subprocess.run(
        [
            sys.executable,
            "src/pirateforce_foundation/skill_learn_request_headless.py",
        ],
        cwd=str(ROOT), env=_plain_env(tmp_path),
        capture_output=True, text=True, timeout=1800,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    assert (
        H.TOKEN_PREFIX + "_SUMMARY probes=3 decoded_no_reply=yes "
        "real_frame=refused no_db_write=yes RESULT=PASS" in done.stdout
    ), done.stdout[-2000:]
    for label in R.LEARN_SKILL_REQUEST_PROBE_ORDER:
        assert H.TOKEN_PREFIX + " case=probe_" + label + " " in done.stdout
    assert H.TOKEN_PREFIX + " case=real_r312_frame70 " in done.stdout


def test_the_proof_refuses_to_run_on_another_checkouts_modules(monkeypatch):
    """A token produced by a foreign tree's decoder names nothing at all."""
    foreign = types.ModuleType("pirateforce_foundation.runtime")
    foreign.__file__ = "/somewhere/else/src/pirateforce_foundation/runtime.py"
    monkeypatch.setitem(
        sys.modules, "pirateforce_foundation.runtime", foreign,
    )
    with pytest.raises(RuntimeError):
        H._refuse_a_foreign_checkout()
