"""MOVE-AUTHORITY-002: the server-side gate on the local player's own position.

WHY THIS MODULE EXISTS -- and what it deliberately does NOT do
--------------------------------------------------------------
``docs/FUNCTIONAL_COVERAGE.json`` names ``local_player_movement_authority`` as
the next missing behavior of the movement domain, and states the gap in one
sentence: the server "accepts client-reported positions without any
validation".  MOVE-AUTHORITY-001 (round 72,
``tests/test_move_authority_targetpos_static.py`` +
``reports/PF_MOVE_AUTHORITY001_TARGETPOS_PRODUCER_STATIC_20260818.md``)
characterized the transport that gap rides, byte-exact from the read-only
client image:

    TargetPosVital(0x2A90), wire schema four f32 (x, y, z, heading) then two
    u8 (moving, mask), decoded server-side by ``parse_target_pos_vital`` /
    ``parse_v141_refresh_target_pos``, after which ``runtime.py``'s
    ``_checkpoint_exact_target`` writes the reported position through to the
    character row with no distance, speed or collision test of any kind.

That milestone was explicitly report-only: "the authority model itself is
uncaptured".  This module is the authority model, and nothing else.  It is a
PURE DECISION FUNCTION over one reported reading plus the previously accepted
one; it performs no I/O, holds no state, touches no database, and composes no
bytes.  The runtime consults it, behind an opt-in scenario, to decide whether a
position checkpoint may be written.

THE ONE THING THIS LANE MAY DO, AND THE ONE THING IT MAY NOT
------------------------------------------------------------
MAY:  refuse the WRITE.  A refused report leaves the persisted position exactly
      as it was and records a named event.  Refusing to write invents nothing.
MAY NOT: send a corrective reposition.  No captured frame, no producer and no
      client-side consumer for a server-initiated "you are actually here"
      correction has ever been found; TELEPORT exists as a transport but what a
      real client does with an unsolicited mid-walk teleport is UNKNOWN.  This
      module therefore never returns bytes and the dispatcher never emits a
      frame on its behalf.  The client-observable half of this lane is
      undecidable here and belongs to an attended test.

PROVENANCE OF EVERY CLAIM THE CODE MAKES
----------------------------------------
* [PROVEN] The report transport, its field order and the server's parse are
  MOVE-AUTHORITY-001, cross-checked against ``current/`` at
  ``parse_v141_refresh_target_pos``: the accepted singleton yields
  ``(x, y, z, heading, 0, moving)``.  Index 4 is a constant zero produced by
  the parser, NOT a client-sent mask; only index 5 carries the client's
  ``moving`` u8.  This module names the field ``moving`` for that reason.
* [PROVEN] The parser already refuses a non-finite component
  (``math.isfinite`` guard) and a non-zero derived mask.  A non-finite reading
  therefore cannot normally reach this module -- the check below is kept as an
  independent fail-closed layer, not as a claim that the parser is missing it.
* [STATIC] The client's const data carries movement speed columns for MOBS
  (``pf_bridge/FACTPACK_R100_CONSTDATA_MONSTER_LOOT.md`` lines 179-180 and 232:
  ``n_SPEED_WALK`` / ``n_SPEED_RUN``, e.g. 100/650 and 100/800).  Those are MOB
  columns in unknown units and there is no PLAYER speed column behind them.
  They are NOT the source of any threshold here and must never be cited as
  one; they are recorded only so a later round does not re-derive them hoping
  they close this question.  They do not.
* [PROVEN, and it cost this lane a budget] MOVE-CADENCE-001 (round 74,
  ``reports/PF_MOVE_CADENCE001_CHECKPOINT_CADENCE_PER_WALK_HEADLESS_20260818.md``)
  replayed the authentic GT-005 boot1 walk capture through this very checkpoint
  gate: 29 TargetPosVital frames produced 19 writes and 10 dedup skips, and the
  ``moving`` flag was 1 on only FIVE of the 29 frames.  Five frames cannot
  produce nineteen distinct positions, so at least fourteen of the nineteen
  legitimate writes in the only authentic walk this project holds arrived with
  ``moving == 0``.  The flag is therefore NOT a usable "am I walking" signal at
  the frame the client sends, and the shipped profile sets
  ``enforce_moving_flag`` to FALSE.  The rung stays implemented and tested
  because it is a policy knob a future profile may want, but any profile that
  turns it on must first explain that measurement away.
* [PROVEN, and it cost this lane a second budget] The same report's replay
  output is committed at ``reports/move_cadence001_smoke/replay_output.txt``
  as a 29-row table (frame ordinal, heartbeat index, x, y, z, heading, moving,
  write/skip).  Replaying those 29 authentic readings through THIS ladder, with
  elapsed taken as the heartbeat delta times the 2.0 s heartbeat period, found
  a false refusal the tests could not have found on synthetic data: rows 60 and
  62 share heartbeat 43, so elapsed came out 0.0 and the reading was refused as
  ``nonpositive_elapsed`` even though the walk was ordinary.  Two reports inside
  one clock tick are normal, and with a real monotonic clock the same pair
  yields a tiny positive elapsed whose quotient is a huge apparent speed -- the
  same false refusal wearing a different name.  The ladder therefore treats an
  elapsed below ``min_measurable_elapsed_seconds`` as UNMEASURABLE rather than
  as evidence of speed, and accepts on the clock-free budgets alone.
  KNOWN GAP, stated rather than hidden: a client that bursts readings faster
  than that floor is bounded only by ``max_step_units`` per reading, so it can
  outrun the speed budget by sending more often.  Closing that needs a windowed
  accumulator, which this checkpoint does not build.
* [PROVEN] The same report gives the arrival cadence: successive distinct frames
  1-3 heartbeats apart during movement (one write per 2-6 s, peak one per 2 s)
  and 19 writes across about 302 s overall.  The per-frame deltas of the one
  continuous moving run were about 400-500 units.  The shipped step budget
  (2000) and speed budget (1200/s, tolerance 0.25) therefore sit several times
  above the only real walk we can measure -- which is headroom, not validation.
* [OUR DESIGN] Everything else: the refusal ladder and its ORDER, the split
  between clock-free and clock-dependent checks, the decision to treat the
  first report of a session as an anchor, the teleport grace window, the
  moving-flag consistency rule, and every numeric budget in the scenario file.
  The original server's movement policy is unrecoverable (the server was never
  published) and is NOT claimed, approximated or reconstructed here.

DETERMINISM
-----------
``evaluate_move_report`` is a pure function of its arguments.  It reads no
clock: the caller passes the elapsed seconds it measured.  Same inputs, same
verdict, on every machine and in every process.

FAIL-CLOSED, AND NEVER SILENTLY
-------------------------------
Every path that is not an explicitly recognized ACCEPT is a refusal with a
named reason.  A malformed argument, an unusable clock reading and an
unrecognized policy are refusals, never silent acceptances.  The scenario
loader refuses by raising, so an unreadable or drifted file can never degrade
into "the gate is off while the operator believes it is on".

NONCLAIMS
---------
* This is not the original server's movement policy.  That policy is
  unrecoverable and is not approximated here.
* KNOWN BYPASS, stated rather than hidden: exactly one reading is admitted
  WITHOUT being measured after each server-initiated teleport, because the
  server moved the player and the gate's baseline is stale by definition.  A
  client that lies in precisely that window writes an arbitrary position, and
  reconnecting re-arms it once (scene entry teleports).  Closing it needs the
  teleport's DESTINATION, which the frozen dispatcher does not hand out in any
  structured form; the label is all there is.  It is bounded at one reading per
  server move and is tested as a gap, not as a feature.
* No client has ever been shown one byte of this lane -- it emits no bytes at
  all.  What a real client does when its report is silently not persisted is
  UNKNOWN and belongs to an attended test.
* The world unit is not convertible to any real-world measure from anything we
  hold, so the budgets are meaningful only against readings in the same
  coordinate space.
* Refusing a write is not collision, terrain or line-of-sight validation.  No
  geometry of the map exists on the server.
* VERTICAL SPEED IS NOT BOUNDED.  Only horizontal displacement is divided by
  elapsed time; ``max_vertical_step_units`` caps one reading's climb but says
  nothing about how often that climb may be repeated, so a client reporting
  399 units of ascent every reading rises without limit and is admitted
  ``within_budget`` at speed 0.0.  Bounding it needs a second rate and a
  reason to pick its number; neither exists yet.
* production_baseline_behavior is untouched: with the scenario absent this
  module is never consulted and the checkpoint path is byte-for-byte the one
  MOVE-AUTHORITY-001 characterized.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple


# PF-HYPOTHESIS-LEDGER: HYP-PF-030 active
MOVE_AUTHORITY_CHECKPOINT = "MOVE-AUTHORITY-002"
MOVE_AUTHORITY_HYPOTHESIS_ID = "HYP-PF-030"
production_allowed = False

# ---- verdict reasons -------------------------------------------------------
# Accept reasons.
REASON_ANCHOR = "anchor"
REASON_STATIONARY = "stationary"
REASON_TELEPORT_GRACE = "teleport_grace"
REASON_WITHIN_BUDGET = "within_budget"
REASON_CLOCK_TOO_COARSE = "clock_too_coarse"
# Refusal reasons.
REASON_MALFORMED_REPORT = "malformed_report"
REASON_NONFINITE_COMPONENT = "nonfinite_component"
REASON_MOVING_FLAG_INCONSISTENT = "moving_flag_inconsistent"
REASON_VERTICAL_OVER_BUDGET = "vertical_over_budget"
REASON_STEP_OVER_BUDGET = "step_over_budget"
REASON_NONPOSITIVE_ELAPSED = "nonpositive_elapsed"
REASON_SPEED_OVER_BUDGET = "speed_over_budget"

ACCEPT_REASONS = (
    REASON_ANCHOR,
    REASON_STATIONARY,
    REASON_TELEPORT_GRACE,
    REASON_WITHIN_BUDGET,
    REASON_CLOCK_TOO_COARSE,
)
REFUSAL_REASONS = (
    REASON_MALFORMED_REPORT,
    REASON_NONFINITE_COMPONENT,
    REASON_MOVING_FLAG_INCONSISTENT,
    REASON_VERTICAL_OVER_BUDGET,
    REASON_STEP_OVER_BUDGET,
    REASON_NONPOSITIVE_ELAPSED,
    REASON_SPEED_OVER_BUDGET,
)


@dataclass(frozen=True)
class MoveAuthorityPolicy:
    """The budgets one scenario file authorizes.  Every number is OUR DESIGN.

    Units are the client's world units for distance and seconds for time.  The
    world unit is NOT convertible to any real-world measure from anything we
    hold, so a budget is meaningful only against other readings in the same
    coordinate space.
    """

    max_step_units: float
    max_speed_units_per_second: float
    max_vertical_step_units: float
    speed_tolerance_ratio: float
    min_measurable_elapsed_seconds: float
    enforce_moving_flag: bool
    teleport_grace_reports: int


@dataclass(frozen=True)
class MoveAuthorityScenario:
    scenario_id: str
    hypothesis_id: str
    policy: MoveAuthorityPolicy


@dataclass(frozen=True)
class MoveAuthorityVerdict:
    """One decision about one report.

    ``accepted`` is the only field the dispatcher acts on; the measurements are
    carried so a test, a report or a headless replay can show its work instead
    of re-deriving it.
    """

    accepted: bool
    reason: str
    horizontal: float
    vertical: float
    speed: Optional[float]

    @property
    def checkpoint_allowed(self) -> bool:
        return self.accepted


# The one allowlisted scenario body.  A file that differs in ANY key or value
# is refused: an opt-in lane whose file can drift is not opt-in.
_SPEED_GATE_POLICY = MoveAuthorityPolicy(
    max_step_units=2000.0,
    max_speed_units_per_second=1200.0,
    max_vertical_step_units=400.0,
    speed_tolerance_ratio=0.25,
    # Below this, a quotient is arithmetic noise rather than a speed: the one
    # authentic walk we hold delivers two readings inside a single 2.0 s
    # heartbeat window.
    min_measurable_elapsed_seconds=0.5,
    # FALSE on the strength of MOVE-CADENCE-001: in the one authentic walk this
    # project holds, at least 14 of 19 legitimate writes carried moving == 0.
    # Turning this on would refuse most of a real walk.
    enforce_moving_flag=False,
    # ONE, not two: this is the window in which a reading is admitted without
    # being measured, so it is also the size of this lane's one known bypass.
    teleport_grace_reports=1,
)

_SPEED_GATE = MoveAuthorityScenario(
    "move_authority_hypothesis_speed_gate",
    MOVE_AUTHORITY_HYPOTHESIS_ID,
    _SPEED_GATE_POLICY,
)

_EXPECTED = {
    "schema": 1,
    "id": _SPEED_GATE.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _SPEED_GATE.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_only",
        "report_transport": "target_pos_vital_0x2A90_singleton",
        "corrective_frame_policy": "never_emitted",
    },
    "policy": {
        "max_step_units": _SPEED_GATE_POLICY.max_step_units,
        "max_speed_units_per_second": (
            _SPEED_GATE_POLICY.max_speed_units_per_second
        ),
        "max_vertical_step_units": _SPEED_GATE_POLICY.max_vertical_step_units,
        "speed_tolerance_ratio": _SPEED_GATE_POLICY.speed_tolerance_ratio,
        "min_measurable_elapsed_seconds": (
            _SPEED_GATE_POLICY.min_measurable_elapsed_seconds
        ),
        "enforce_moving_flag": _SPEED_GATE_POLICY.enforce_moving_flag,
        "teleport_grace_reports": _SPEED_GATE_POLICY.teleport_grace_reports,
    },
    "capabilities": [
        "refuse_position_checkpoint_when_report_exceeds_our_budget",
        "record_named_verdict_event_for_every_report",
    ],
    "nonclaims": [
        "original_server_movement_policy",
        "corrective_reposition_wire_shape",
        "client_observable_acceptance",
        "vertical_speed_is_unbounded",
        "unit_of_measure_of_client_world_coordinates",
        "production_baseline_behavior",
    ],
}

_PROFILES = {_SPEED_GATE.scenario_id: _SPEED_GATE}


def _exact_equal(actual: Any, expected: Any) -> bool:
    """Type-strict recursive equality.

    Plain ``==`` would accept ``True`` where ``1`` is expected and ``2`` where
    ``2.0`` is expected.  A permission token that accepts near misses is not a
    permission token, so every node is compared by type first.
    """
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        if set(actual) != set(expected):
            return False
        return all(_exact_equal(actual[key], expected[key]) for key in expected)
    if type(expected) is list:
        if len(actual) != len(expected):
            return False
        return all(
            _exact_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def require_move_authority_hypothesis_scenario(value: Any) -> MoveAuthorityScenario:
    """Refuse anything that is not the module's own frozen profile.

    Compared by identity, so a value-equal lookalike dataclass built outside
    this module opens nothing.
    """
    if not any(value is profile for profile in _PROFILES.values()):
        raise ValueError(
            "move_authority_scenario_not_allowlisted: HYP-PF-030 refuses to "
            "gate position checkpoints on a profile this module did not issue"
        )
    return value


def load_move_authority_hypothesis_scenario(path) -> MoveAuthorityScenario:
    """Load the one allowlisted opt-in scenario file, or refuse by name.

    The file is a PERMISSION TOKEN, never a source of values: the budgets the
    gate uses are the module's own frozen profile.  A file that differs from
    the allowlisted body anywhere -- one extra key, one missing key, one int
    where a float is expected -- is refused.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "move_authority_scenario_unreadable: HYP-PF-030 refuses an "
            "unreadable or malformed opt-in file"
        ) from exc
    if type(data) is not dict or data.get("id") not in _PROFILES:
        raise ValueError(
            "move_authority_scenario_unknown_id: HYP-PF-030 refuses a file "
            "that does not name the one allowlisted profile"
        )
    if not _exact_equal(data, _EXPECTED):
        raise ValueError(
            "move_authority_scenario_exceeds_allowlist: HYP-PF-030 refuses a "
            "scenario body that drifted from the allowlisted one"
        )
    return require_move_authority_hypothesis_scenario(_PROFILES[data["id"]])


def _finite(values: Sequence[Any]) -> bool:
    for value in values:
        # type(), not isinstance(): bool IS an int in Python and a bool
        # coordinate is a malformed reading, not a zero.
        if type(value) not in (int, float):
            return False
        if not math.isfinite(float(value)):
            return False
    return True


def _refuse(reason: str, horizontal: float, vertical: float,
            speed: Optional[float] = None) -> MoveAuthorityVerdict:
    return MoveAuthorityVerdict(False, reason, horizontal, vertical, speed)


def evaluate_move_report(
    previous: Optional[Tuple[float, float, float]],
    report: Sequence[Any],
    elapsed_seconds: Optional[float],
    policy: MoveAuthorityPolicy,
    *,
    grace: bool = False,
) -> MoveAuthorityVerdict:
    """Decide whether one reported position may be persisted.

    ``previous`` is the last position this session actually accepted, or None
    for the first report.  ``report`` is the parser's tuple
    ``(x, y, z, heading, 0, moving)`` -- index 4 is the parser's constant zero
    and is not read here.  ``elapsed_seconds`` is the caller-measured wall time
    since the last accepted report; None means the caller has no usable
    reading.

    THE LADDER, in order.  Clock-free checks come first on purpose: a verdict
    that does not depend on a clock is reproducible from the frames alone.

      1. malformed argument or unknown policy   -> refuse malformed_report
      2. any non-finite coordinate              -> refuse nonfinite_component
      3. grace window open                      -> accept teleport_grace
      4. no previously accepted position        -> accept anchor
      5. no displacement at all                 -> accept stationary
      6. moving flag says standing, yet moved   -> refuse moving_flag_inconsistent
      7. |dz| over the vertical budget          -> refuse vertical_over_budget
      8. one step over the step budget          -> refuse step_over_budget
      9. elapsed missing, unusable or negative  -> refuse nonpositive_elapsed
     10. elapsed below the measurable floor     -> accept clock_too_coarse
     11. displacement/elapsed over the speed
         budget plus tolerance                  -> refuse speed_over_budget
     12. otherwise                              -> accept within_budget
    """
    if type(policy) is not MoveAuthorityPolicy:
        return _refuse(REASON_MALFORMED_REPORT, 0.0, 0.0)
    if type(report) not in (tuple, list) or len(report) < 6:
        return _refuse(REASON_MALFORMED_REPORT, 0.0, 0.0)
    if not _finite(report[:4]):
        return _refuse(REASON_NONFINITE_COMPONENT, 0.0, 0.0)

    x, y, z = float(report[0]), float(report[1]), float(report[2])
    moving = report[5]
    if type(moving) is not int:
        return _refuse(REASON_MALFORMED_REPORT, 0.0, 0.0)

    if grace:
        return MoveAuthorityVerdict(
            True, REASON_TELEPORT_GRACE, 0.0, 0.0, None,
        )

    if previous is None:
        return MoveAuthorityVerdict(True, REASON_ANCHOR, 0.0, 0.0, None)
    if type(previous) not in (tuple, list) or len(previous) != 3:
        return _refuse(REASON_MALFORMED_REPORT, 0.0, 0.0)
    if not _finite(previous):
        return _refuse(REASON_MALFORMED_REPORT, 0.0, 0.0)

    horizontal = math.hypot(x - float(previous[0]), y - float(previous[1]))
    vertical = abs(z - float(previous[2]))

    if horizontal == 0.0 and vertical == 0.0:
        return MoveAuthorityVerdict(
            True, REASON_STATIONARY, 0.0, 0.0, None,
        )
    if policy.enforce_moving_flag and moving == 0 and horizontal > 0.0:
        return _refuse(REASON_MOVING_FLAG_INCONSISTENT, horizontal, vertical)
    if vertical > policy.max_vertical_step_units:
        return _refuse(REASON_VERTICAL_OVER_BUDGET, horizontal, vertical)
    if horizontal > policy.max_step_units:
        return _refuse(REASON_STEP_OVER_BUDGET, horizontal, vertical)

    if elapsed_seconds is None or not _finite((elapsed_seconds,)):
        return _refuse(REASON_NONPOSITIVE_ELAPSED, horizontal, vertical)
    elapsed = float(elapsed_seconds)
    if elapsed < 0.0:
        # A clock that ran backwards tells us nothing; it does not tell us the
        # reading is good.
        return _refuse(REASON_NONPOSITIVE_ELAPSED, horizontal, vertical)
    if elapsed < policy.min_measurable_elapsed_seconds:
        # Two readings inside one tick.  Dividing here manufactures a speed out
        # of clock granularity, and that false speed is a false refusal.  The
        # clock-free budgets above have already passed, so this is an accept
        # with its own name -- never folded into within_budget, so a reader can
        # count how often the clock was the deciding factor.
        return MoveAuthorityVerdict(
            True, REASON_CLOCK_TOO_COARSE, horizontal, vertical, None,
        )

    speed = horizontal / elapsed
    ceiling = policy.max_speed_units_per_second * (
        1.0 + policy.speed_tolerance_ratio
    )
    if speed > ceiling:
        return _refuse(REASON_SPEED_OVER_BUDGET, horizontal, vertical, speed)

    return MoveAuthorityVerdict(
        True, REASON_WITHIN_BUDGET, horizontal, vertical, speed,
    )
