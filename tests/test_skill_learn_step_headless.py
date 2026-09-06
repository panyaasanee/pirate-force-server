"""GT-276: one learn-skill-result frame per accepted trigger, and the sweep
file must keep behaving exactly as it does today.

These are the guards that stand between an attended runner and a wasted boot
on Panya's machine: if a step scenario ever emitted the wrong step's bytes
under the right label, GT-276 would blame the wrong frame for the walk lock
and nobody at the screen could tell.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    learn_skill_result_hypothesis as L,
)
from pirateforce_foundation import (  # noqa: E402
    skill_learn_step_headless as H,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

SWEEP = ROOT / "scenarios" / "learn_skill_result_hypothesis_learn_sweep.json"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


@pytest.fixture(scope="module")
def legacy():
    return load_legacy(LEGACY_PATH)


@pytest.fixture(autouse=True)
def _one_plan_per_test(monkeypatch):
    """A process serves one plan; a test is a process's worth of one boot."""
    monkeypatch.setattr(L, "_ACTIVE_STEP_PLAN", None, raising=False)


def test_the_committed_sweep_file_is_byte_for_byte_what_it_always_was():
    assert json.loads(SWEEP.read_text(encoding="utf-8")) == L._expected_sweep()


def test_loading_the_sweep_still_orders_all_six_steps():
    scenario = L.load_learn_skill_result_hypothesis_scenario(SWEEP)
    assert scenario.scenario_id == L.LEARN_SKILL_RESULT_SCENARIO_ID
    assert scenario.step_order == L.LEARN_SKILL_RESULT_STEP_ORDER
    assert len(scenario.step_order) == 6
    # and the composer keeps resolving the dispatcher's index against it
    assert L._active_step_order() == L.LEARN_SKILL_RESULT_STEP_ORDER


@pytest.mark.parametrize("label", L.LEARN_SKILL_RESULT_STEP_ORDER)
def test_every_step_has_a_committed_file_that_narrows_the_plan_to_it(label):
    path = H.scenario_path(label)
    assert path.is_file(), path
    scenario = L.load_learn_skill_result_hypothesis_scenario(path)
    assert scenario.step_order == (label,)
    assert scenario.hypothesis_id == L.LEARN_SKILL_RESULT_HYPOTHESIS_ID
    body = json.loads(path.read_text(encoding="utf-8"))
    assert body["test_only"] is True
    assert body["production_allowed"] is False
    assert body["dispatch"]["frames_per_accepted_request"] == 1


@pytest.mark.parametrize("index", range(6))
def test_a_step_boot_composes_that_step_and_never_the_sweeps_first_frame(
    index, legacy,
):
    label = L.LEARN_SKILL_RESULT_STEP_ORDER[index]
    L.load_learn_skill_result_hypothesis_scenario(H.scenario_path(label))
    # this is the call runtime.py makes: it always hands back position 0 for
    # a one-step plan, and position 0 of the SWEEP is COUNT0_TRAIL0
    pc, frame = L.make_learn_skill_result_step_response(legacy, 0)
    want_pc, want_frame = L.make_learn_skill_result_response(
        legacy,
        L.LEARN_SKILL_RESULT_STEP_RECORDS[label],
        L.LEARN_SKILL_RESULT_STEP_TRAILING[label],
    )
    assert (pc, frame) == (want_pc, want_frame)
    if index != 0:
        sweep_first, _ = L.make_learn_skill_result_response(
            legacy,
            L.LEARN_SKILL_RESULT_STEP_RECORDS[
                L.LEARN_SKILL_RESULT_STEP_ORDER[0]
            ],
            L.LEARN_SKILL_RESULT_STEP_TRAILING[
                L.LEARN_SKILL_RESULT_STEP_ORDER[0]
            ],
        )
        assert pc != sweep_first


def test_a_step_boot_refuses_a_second_frame():
    label = L.LEARN_SKILL_RESULT_STEP_ORDER[2]
    L.load_learn_skill_result_hypothesis_scenario(H.scenario_path(label))
    assert L._active_step_order() == (label,)


def test_one_process_will_not_be_re_aimed_at_another_step():
    order = L.LEARN_SKILL_RESULT_STEP_ORDER
    L.load_learn_skill_result_hypothesis_scenario(H.scenario_path(order[1]))
    with pytest.raises(RuntimeError):
        L.load_learn_skill_result_hypothesis_scenario(
            H.scenario_path(order[2])
        )


def test_a_step_file_with_one_edited_value_is_refused(tmp_path):
    label = L.LEARN_SKILL_RESULT_STEP_ORDER[1]
    body = json.loads(H.scenario_path(label).read_text(encoding="utf-8"))
    body["dispatch"]["frames_per_accepted_request"] = 6
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(ValueError):
        L.load_learn_skill_result_hypothesis_scenario(path)


def test_an_unknown_scenario_id_is_still_refused_by_name(tmp_path):
    body = json.loads(SWEEP.read_text(encoding="utf-8"))
    body["id"] = "learn_skill_result_hypothesis_learn_step_count9_trail9"
    path = tmp_path / "unknown.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(ValueError):
        L.load_learn_skill_result_hypothesis_scenario(path)


def test_the_gate_object_still_refuses_a_hand_built_scenario():
    with pytest.raises(ValueError):
        L.require_learn_skill_result_hypothesis_scenario(
            L.LearnSkillResultHypothesisScenario(
                L.learn_skill_result_step_scenario_id(
                    L.LEARN_SKILL_RESULT_STEP_ORDER[0]
                ),
                L.LEARN_SKILL_RESULT_HYPOTHESIS_ID,
                ("COUNT0_TRAIL0", "COUNT1_TRAIL0"),
                L.LEARN_SKILL_RESULT_SPACING_SECONDS,
            )
        )


def test_the_headless_proof_arms_one_step_through_the_real_dispatcher():
    label = L.LEARN_SKILL_RESULT_STEP_ORDER[1]
    line = H.prove_one_step(label)
    assert line.startswith(H.TOKEN_PREFIX + " step=" + label + " actions=1 ")
    assert L.LEARN_SKILL_RESULT_ACTION_LABEL_PREFIX + label in line
    assert line.isascii()


@pytest.mark.parametrize("index", range(6))
def test_the_gate_alone_selects_the_plan_it_admits(index, legacy):
    """The object gate is the whole gate -- accept and select are one act.

    A caller that reaches the composer through require_() without ever
    calling load_() (runtime.py re-checks the object it was handed, and any
    future caller may do the same) used to get a step profile accepted while
    the plan stayed the module's six-step order: index 0 then composed
    COUNT0_TRAIL0's bytes under the admitted step's action label, with every
    pin green.  That is GT-276's question inverted, so it is closed here.
    """
    label = L.LEARN_SKILL_RESULT_STEP_ORDER[index]
    scenario = L.require_learn_skill_result_hypothesis_scenario(
        L._PROFILE_LEARN_STEP[label]
    )
    assert scenario.step_order == (label,)
    assert L._active_step_order() == (label,)
    pc, frame = L.make_learn_skill_result_step_response(legacy, 0)
    want_pc, want_frame = L.make_learn_skill_result_response(
        legacy,
        L.LEARN_SKILL_RESULT_STEP_RECORDS[label],
        L.LEARN_SKILL_RESULT_STEP_TRAILING[label],
    )
    assert (pc, frame) == (want_pc, want_frame)
    if index != 0:
        sweep_first, _ = L.make_learn_skill_result_response(
            legacy,
            L.LEARN_SKILL_RESULT_STEP_RECORDS[
                L.LEARN_SKILL_RESULT_STEP_ORDER[0]
            ],
            L.LEARN_SKILL_RESULT_STEP_TRAILING[
                L.LEARN_SKILL_RESULT_STEP_ORDER[0]
            ],
        )
        assert pc != sweep_first


def test_the_gate_admits_the_sweep_without_narrowing_anything():
    """No step file loaded stays exactly the shipped six-step behaviour."""
    scenario = L.require_learn_skill_result_hypothesis_scenario(
        L._PROFILE_LEARN_SWEEP
    )
    assert scenario.step_order == L.LEARN_SKILL_RESULT_STEP_ORDER
    assert L._active_step_order() == L.LEARN_SKILL_RESULT_STEP_ORDER
    assert L._ACTIVE_STEP_PLAN is None


def test_re_checking_the_same_step_object_twice_is_not_a_re_aiming():
    """runtime.py re-checks what app.py loaded; that must stay a no-op."""
    label = L.LEARN_SKILL_RESULT_STEP_ORDER[3]
    scenario = L.load_learn_skill_result_hypothesis_scenario(
        H.scenario_path(label)
    )
    again = L.require_learn_skill_result_hypothesis_scenario(scenario)
    assert again is scenario
    assert L._active_step_order() == (label,)


def test_the_gate_refuses_a_second_step_object_in_one_process():
    order = L.LEARN_SKILL_RESULT_STEP_ORDER
    L.require_learn_skill_result_hypothesis_scenario(
        L._PROFILE_LEARN_STEP[order[1]]
    )
    with pytest.raises(RuntimeError):
        L.require_learn_skill_result_hypothesis_scenario(
            L._PROFILE_LEARN_STEP[order[2]]
        )


def test_a_refused_object_never_reaches_the_plan(legacy):
    """Validation happens before selection: a refusal leaves no residue."""
    with pytest.raises(ValueError):
        L.require_learn_skill_result_hypothesis_scenario(
            L.LearnSkillResultHypothesisScenario(
                L.learn_skill_result_step_scenario_id(
                    L.LEARN_SKILL_RESULT_STEP_ORDER[2]
                ),
                L.LEARN_SKILL_RESULT_HYPOTHESIS_ID,
                (L.LEARN_SKILL_RESULT_STEP_ORDER[2],),
                L.LEARN_SKILL_RESULT_SPACING_SECONDS + 1.0,
            )
        )
    assert L._ACTIVE_STEP_PLAN is None
    assert L._active_step_order() == L.LEARN_SKILL_RESULT_STEP_ORDER


def test_the_documented_command_runs_on_a_plain_checkout(tmp_path):
    """NOW.md has ka1-A re-run this proof before an attended boot.

    It runs from a checkout with nothing installed and no PYTHONPATH, so the
    command printed in the module docstring and in the ticket has to work in
    exactly that state, not only under pytest.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("PYTHONPATH", "PYTHONHOME")
    }
    env["TMPDIR"] = str(tmp_path)
    label = L.LEARN_SKILL_RESULT_STEP_ORDER[1]
    done = subprocess.run(
        [
            sys.executable,
            "src/pirateforce_foundation/skill_learn_step_headless.py",
            "--step",
            label,
        ],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=600,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    assert (
        H.TOKEN_PREFIX + " step=" + label + " actions=1 " in done.stdout
    ), done.stdout[-2000:]
