#!/usr/bin/env python3
"""MOVE-AUTHORITY-002 (HYP-PF-030) offline verifier: the gate, re-derived.

Runs the movement-authority policy against expectations this file computes
FOR ITSELF -- its own hypot, its own ceiling arithmetic, its own reading of
the scenario file -- so a bug that lives in the module's arithmetic cannot
hide behind the module's own helpers.  Pure stdlib, no database, no socket,
no artifact: it runs on any fresh clone.

Exit 0 = every guard passed.  Exit 1 = at least one guard failed, and the
failing guard is printed with what it wanted and what it got.
"""
from __future__ import annotations

import dataclasses

import ast
import json
import math
import os
import sys
import tempfile
from pathlib import Path


# PF_MOVE_AUTHORITY_ROOT lets a test run a deliberately BROKEN copy of this
# file from outside the tree and still have it find the artifacts, which is how
# the suite proves this verifier can go red at all.
ROOT = Path(
    os.environ.get("PF_MOVE_AUTHORITY_ROOT")
    or Path(__file__).resolve().parents[1]
)
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import move_authority_hypothesis as mah  # noqa: E402

SCENARIO = ROOT / "scenarios" / "move_authority_hypothesis_speed_gate.json"
MODULE = ROOT / "src" / "pirateforce_foundation" / "move_authority_hypothesis.py"

FAILURES: list[str] = []
GUARDS = 0


def guard(name: str, wanted, got) -> None:
    global GUARDS
    GUARDS += 1
    if wanted != got:
        FAILURES.append(f"{name}: wanted {wanted!r}, got {got!r}")


def report(x=0.0, y=0.0, z=0.0, heading=0.0, moving=1):
    return (x, y, z, heading, 0, moving)


def main() -> int:
    body = json.loads(SCENARIO.read_text(encoding="utf-8"))
    source = MODULE.read_text(encoding="utf-8")

    # ---- 1. the file is a permission token and says so ---------------------
    guard("scenario test_only", True, body["test_only"])
    guard("scenario production_allowed", False, body["production_allowed"])
    guard("scenario hypothesis id", "HYP-PF-030", body["hypothesis_id"])
    guard(
        "scenario emits no corrective frame",
        "never_emitted", body["entry"]["corrective_frame_policy"],
    )
    for nonclaim in (
        "original_server_movement_policy",
        "corrective_reposition_wire_shape",
        "client_observable_acceptance",
        "unit_of_measure_of_client_world_coordinates",
        "production_baseline_behavior",
    ):
        guard(f"nonclaim {nonclaim}", True, nonclaim in body["nonclaims"])

    # ---- 2. the loaded profile is the module's own, not the file's ---------
    scenario = mah.load_move_authority_hypothesis_scenario(SCENARIO)
    policy = scenario.policy
    guard("loaded profile identity", True, scenario is mah._SPEED_GATE)
    for key, value in body["policy"].items():
        guard(f"policy {key} matches the file", value, getattr(policy, key))
        guard(f"policy {key} type", type(value), type(getattr(policy, key)))

    # ---- 3. the module composes nothing and touches nothing ----------------
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    guard(
        "module imports only the declared stdlib",
        {"__future__", "dataclasses", "json", "math", "pathlib", "typing"},
        imported,
    )
    for banned in ("sqlite3", "socket", "u8tag", "u16tag", "f32tag"):
        guard(f"module never names {banned}", False, banned in imported
              or f"{banned}(" in source)
    guard(
        "module carries exactly one ledger marker", 1,
        source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-030 active"),
    )
    guard("module refuses production", False, mah.production_allowed)

    # ---- 4. the ladder, against arithmetic computed here -------------------
    origin = (0.0, 0.0, 0.0)
    ceiling = policy.max_speed_units_per_second * (
        1.0 + policy.speed_tolerance_ratio
    )

    guard(
        "first report anchors", mah.REASON_ANCHOR,
        mah.evaluate_move_report(None, report(9.0, 9.0), None, policy).reason,
    )
    guard(
        "grace accepts before measuring", mah.REASON_TELEPORT_GRACE,
        mah.evaluate_move_report(
            origin, report(1e6, 1e6), 0.001, policy, grace=True,
        ).reason,
    )
    guard(
        "a non-finite reading outranks grace", mah.REASON_NONFINITE_COMPONENT,
        mah.evaluate_move_report(
            origin, report(float("nan")), 1.0, policy, grace=True,
        ).reason,
    )
    guard(
        "no displacement needs no clock", mah.REASON_STATIONARY,
        mah.evaluate_move_report(origin, report(0.0, 0.0, 0.0, 2.0, 0),
                                 None, policy).reason,
    )
    # The shipped profile does not read the moving flag -- the authentic walk
    # of MOVE-CADENCE-001 is why -- so the rung is exercised on a profile that
    # turns it on, and the shipped profile is checked to leave it alone.
    strict = dataclasses.replace(policy, enforce_moving_flag=True)
    guard("shipped profile ignores the moving flag", False,
          policy.enforce_moving_flag)
    guard(
        "moving flag outranks the distance budgets",
        mah.REASON_MOVING_FLAG_INCONSISTENT,
        mah.evaluate_move_report(
            origin,
            report(policy.max_step_units * 9, 0.0,
                   policy.max_vertical_step_units * 9, moving=0),
            1.0, strict,
        ).reason,
    )
    guard(
        "the shipped profile admits the same reading",
        mah.REASON_WITHIN_BUDGET,
        mah.evaluate_move_report(
            origin, report(10.0, 0.0, moving=0), 1.0, policy,
        ).reason,
    )
    guard(
        "vertical outranks step", mah.REASON_VERTICAL_OVER_BUDGET,
        mah.evaluate_move_report(
            origin,
            report(policy.max_step_units * 9, 0.0,
                   policy.max_vertical_step_units + 1.0),
            1.0, policy,
        ).reason,
    )
    guard(
        "step is refused without a clock", mah.REASON_STEP_OVER_BUDGET,
        mah.evaluate_move_report(
            origin, report(policy.max_step_units + 1.0), None, policy,
        ).reason,
    )
    for elapsed in (None, -1.0):
        guard(
            f"elapsed {elapsed!r} refuses", mah.REASON_NONPOSITIVE_ELAPSED,
            mah.evaluate_move_report(
                origin, report(10.0), elapsed, policy,
            ).reason,
        )
    # A clock too coarse to divide by is not evidence of speed.
    floor = policy.min_measurable_elapsed_seconds
    guard("floor is positive", True, floor > 0.0)
    for elapsed in (0.0, floor / 2.0):
        guard(
            f"elapsed {elapsed!r} is admitted unmeasured",
            mah.REASON_CLOCK_TOO_COARSE,
            mah.evaluate_move_report(
                origin, report(10.0), elapsed, policy,
            ).reason,
        )
    guard(
        "the clock-free budgets still apply below the floor",
        mah.REASON_STEP_OVER_BUDGET,
        mah.evaluate_move_report(
            origin, report(policy.max_step_units + 1.0), 0.0, policy,
        ).reason,
    )

    # The speed edge, both sides of it, with the ceiling recomputed here.
    for offset, wanted in ((-1.0, mah.REASON_WITHIN_BUDGET),
                           (+1.0, mah.REASON_SPEED_OVER_BUDGET)):
        distance = ceiling + offset
        verdict = mah.evaluate_move_report(
            origin, report(distance, 0.0), 1.0, policy,
        )
        guard(f"speed edge {offset:+.0f}", wanted, verdict.reason)
        guard(
            f"speed edge {offset:+.0f} shows its work",
            round(distance, 6), round(verdict.speed, 6),
        )

    # Measurements, against this file's own hypot.
    for dx, dy, dz in ((300.0, 400.0, 0.0), (30.0, 40.0, 12.0),
                       (7.0, 24.0, 3.0)):
        verdict = mah.evaluate_move_report(
            origin, report(dx, dy, dz), 1.0, policy,
        )
        guard(
            f"horizontal of ({dx},{dy})",
            round(math.hypot(dx, dy), 6), round(verdict.horizontal, 6),
        )
        guard(f"vertical of {dz}", round(abs(dz), 6), round(verdict.vertical, 6))

    # ---- 5. every refusal is named, and named from the declared set --------
    seen = set()
    seen.add(mah.evaluate_move_report(
        origin, report(10.0, 0.0, moving=0), 1.0, strict,
    ).reason)
    for previous, rep, elapsed, grace in (
        (None, report(1.0), None, False),
        (origin, report(0.0), None, False),
        (origin, report(5.0), 1.0, False),
        (origin, report(1e6), 1.0, True),
        (origin, report(float("inf")), 1.0, False),
        (origin, report(10.0, moving=0), 1.0, False),
        (origin, report(0.0, 0.0, 1e6), 1.0, False),
        (origin, report(1e6), 1.0, False),
        (origin, report(10.0), None, False),
        (origin, report(10.0), 0.0, False),
        (origin, report(ceiling + 1.0), 1.0, False),
        (origin, (1.0, 2.0), 1.0, False),
    ):
        verdict = mah.evaluate_move_report(
            previous, rep, elapsed, policy, grace=grace,
        )
        pool = mah.ACCEPT_REASONS if verdict.accepted else mah.REFUSAL_REASONS
        guard(f"reason {verdict.reason} is declared", True, verdict.reason in pool)
        guard(
            f"checkpoint_allowed tracks accepted for {verdict.reason}",
            verdict.accepted, verdict.checkpoint_allowed,
        )
        seen.add(verdict.reason)
    # No union with anything: a reachability guard that adds the reason it is
    # checking for cannot fail for the reason it names.
    guard(
        "every declared reason is reachable",
        set(mah.ACCEPT_REASONS) | set(mah.REFUSAL_REASONS),
        seen,
    )

    # ---- 6. a drifted or forged permission token opens nothing -------------
    for tamper in (
        ('"max_speed_units_per_second": 1200.0',
         '"max_speed_units_per_second": 999999.0'),
        ('"production_allowed": false', '"production_allowed": true'),
        ('"max_step_units": 2000.0', '"max_step_units": 2000'),
    ):
        text = SCENARIO.read_text(encoding="utf-8").replace(*tamper)
        # Written outside the repository on purpose: a verifier that leaves a
        # file behind in the tree it verifies is a verifier that can change
        # what the next run sees.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tampered.json"
            path.write_text(text, encoding="utf-8")
            try:
                mah.load_move_authority_hypothesis_scenario(path)
                refused = False
            except ValueError:
                refused = True
        guard(f"tampered {tamper[0][:28]} refused", True, refused)

    lookalike = mah.MoveAuthorityScenario(
        scenario.scenario_id, scenario.hypothesis_id, scenario.policy,
    )
    guard("a lookalike compares equal", True, lookalike == scenario)
    try:
        mah.require_move_authority_hypothesis_scenario(lookalike)
        refused = False
    except ValueError:
        refused = True
    guard("a lookalike profile is refused", True, refused)

    print(f"guards run: {GUARDS}")
    for failure in FAILURES:
        print(f"FAIL {failure}")
    print("RESULT: PASS" if not FAILURES else "RESULT: FAIL")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
