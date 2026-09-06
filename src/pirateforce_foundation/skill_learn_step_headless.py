"""GT-276 arming proof: ONE learn-skill-result frame per accepted trigger.

Why this file exists
--------------------
GT-249 / R312 sent all six steps of the pinned HYP-PF-033 sweep on one
accepted trigger and the client could not walk afterwards.  GT-276 asks
which step did it.  Answering that needs the dispatcher to emit exactly one
frame per trigger, and NOW.md requires every attended ticket to carry a
``HEADLESS_PROOF:`` line -- a console token from a headless run on the
current commit showing the mechanism is armed -- before it boards the
capture bus.

This module IS that run.  It drives the real dispatcher through the real
scenario gate on a throwaway database and prints one ASCII token per step.

What the token is entitled to say -- and what it is not
------------------------------------------------------
It says: on this commit, booting with the named step scenario file, one
accepted chat trigger makes the production dispatcher emit EXACTLY ONE
action, carrying the action label of that step and the bytes the pinned
composer produces for that step and no other.

It does NOT say the client accepts the frame, draws anything, or locks the
walk -- nothing here has a client in it.  That is exactly the question
GT-276 puts to an attended run, and this proof does not pre-empt one word
of it.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import learn_skill_result_hypothesis as L  # noqa: E402
from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PROBE_REQUEST_PCS,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

TOKEN_PREFIX = "LEARN_SKILL_STEP_ARMED"
SCENARIOS = ROOT / "scenarios"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


def scenario_path(label: str) -> Path:
    """The committed step scenario file that isolates LABEL."""
    return SCENARIOS / (L.learn_skill_result_step_scenario_id(label) + ".json")


def arm_one_step(label: str) -> tuple[int, str, bytes, bytes]:
    """Boot the real dispatcher on one step file; return what it emitted."""
    scenario = L.load_learn_skill_result_hypothesis_scenario(
        scenario_path(label)
    )
    if scenario.step_order != (label,):
        raise RuntimeError("step scenario did not narrow the plan")
    legacy = load_legacy(LEGACY_PATH)
    with tempfile.TemporaryDirectory() as tmp:
        store = SQLiteStore(Path(tmp) / "gt276.sqlite3", ROOT / "migrations")
        store.migrate()
        state_type = make_state_class(
            legacy,
            CharacterLifecycle(
                store,
                Position(
                    1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                    legacy.V135_PLAYER_Z,
                ),
                legacy.extract_avatar_attr_wire_from_actor,
            ),
            LegacyProjector(legacy),
            learn_skill_result_hypothesis_scenario=scenario,
        )
        state = state_type("gt276_arming")
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc("gt276_arming")))
        characters = store.list_characters(state.foundation.account_id)
        if not characters:
            state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
            characters = store.list_characters(state.foundation.account_id)
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(characters[-1].selector)))
        state.runtime_ack_sent = True
        actions = state.dispatch(legacy.parse_outer(
            CHAT_INPUT_PROBE_REQUEST_PCS["probe1"]))
    if len(actions) != 1:
        raise RuntimeError("dispatcher emitted %d actions" % len(actions))
    return len(actions), actions[0][0], actions[0][1], actions[0][2]


def prove_one_step(label: str) -> str:
    """Run one step and return its console token line."""
    count, action_label, pc, frame = arm_one_step(label)
    expected = L.LEARN_SKILL_RESULT_ACTION_LABEL_PREFIX + label
    if action_label != expected:
        raise RuntimeError("wrong action label %s" % ascii(action_label))
    # The bytes must be the pinned composer's for THIS label and for no
    # other, or a one-step boot would be quietly replaying the sweep's
    # first frame under this step's name.
    for other in L.LEARN_SKILL_RESULT_STEP_ORDER:
        other_pc, _ = L.make_learn_skill_result_response(
            load_legacy(LEGACY_PATH),
            L.LEARN_SKILL_RESULT_STEP_RECORDS[other],
            L.LEARN_SKILL_RESULT_STEP_TRAILING[other],
        )
        if (other_pc == pc) != (other == label):
            raise RuntimeError("step bytes do not identify %s" % label)
    return "%s step=%s actions=%d label=%s pc_bytes=%d frame_bytes=%d" % (
        TOKEN_PREFIX, label, count, action_label, len(pc), len(frame),
    )


def _run_every_step() -> int:
    """Each step needs its own process: one process serves one plan."""
    lines = []
    for label in L.LEARN_SKILL_RESULT_STEP_ORDER:
        done = subprocess.run(
            [sys.executable, "-m", __spec__.name, "--step", label],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        sys.stdout.write(done.stdout)
        sys.stderr.write(done.stderr)
        if done.returncode != 0:
            print("%s_SUMMARY steps=0 RESULT=FAIL step=%s"
                  % (TOKEN_PREFIX, label))
            return 1
        lines.append(label)
    print("%s_SUMMARY steps=%d one_frame_each=yes RESULT=PASS"
          % (TOKEN_PREFIX, len(lines)))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--step" in argv:
        label = argv[argv.index("--step") + 1]
        print(prove_one_step(label))
        return 0
    return _run_every_step()


if __name__ == "__main__":
    raise SystemExit(main())
