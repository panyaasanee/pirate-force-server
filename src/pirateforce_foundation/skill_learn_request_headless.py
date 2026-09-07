"""LEARN-SKILL-REQUEST-001 arming proof: the 0x36AA decoder on a real boot.

Why this file exists
--------------------
NOW.md (PANYA 0159) requires every attended ticket to carry a
``HEADLESS_PROOF:`` line -- a console token from a headless run on the
CURRENT main commit showing the mechanism is armed in the target scene --
before the ticket boards the capture bus.  COO-DECISION 20260907_1141 item 2
ordered LANE-CS to raise the attended ticket for this lane.  This module IS
that proof run.

It boots the REAL dispatcher through the REAL scenario gate on a throwaway
database and prints one ASCII token per case:

  * three PROBE cases (ZERO / MID / MAX) -- a 0x36AA request in the envelope
    this lane accepts is decoded to its two opaque declared values, counted,
    and answered with NOTHING; the database file is byte-identical after.
  * one REAL case -- the bytes a real client actually sent, ka1-A's captured
    frame #70 of round R312 (GT-249), reach the same armed dispatcher and are
    REFUSED as ``wrong_envelope`` because that real frame carries TWO nested
    vitals and this lane accepts one.  That refusal is the measured state of
    the lane today, not a defect this proof hides.

What the token is entitled to say -- and what it is not
------------------------------------------------------
It says: on this commit, booting with
``scenarios/learn_skill_request_hypothesis_decode_probe.json``, the 0x36AA
branch EXISTS, decodes the proven body shape, records the two values, replies
with nothing, writes nothing -- and still fails closed on the real captured
envelope.

It does NOT say a client ever emits 0x36AA on purpose, which UI action makes
it do so, what the two values MEAN, or that anything appears on screen.  Those
are exactly the questions the attended ticket puts to a human at the game
client, and this proof does not pre-empt one word of them.

How to run it
-------------
From the repository root, with no PYTHONPATH and nothing installed::

    python3 src/pirateforce_foundation/skill_learn_request_headless.py

One case only, same command with ``--probe MID`` or ``--real`` appended.

``python3 -m pirateforce_foundation.skill_learn_request_headless`` needs
``src`` on PYTHONPATH already and is NOT the documented form: the ticket's
re-run happens on a plain checkout.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
ROOT = _THIS_FILE.parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    learn_skill_request_hypothesis as R,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


def _refuse_a_foreign_checkout() -> None:
    """Every module in this proof must come from THIS tree, or say so loudly.

    The bootstrap above only inserts ``src`` when it is absent from
    ``sys.path``, so a PYTHONPATH naming another checkout's ``src`` FIRST
    wins: this file would drive that tree's decoder, gate and dispatcher
    while the token names this commit.  ka1-A re-runs this proof before an
    attended boot and culls the ticket when it does not reproduce, so a token
    that can be produced by code from a different commit is worse than no
    token at all.
    """
    home = str(ROOT / "src")
    for module in (
        "pirateforce_foundation.learn_skill_request_hypothesis",
        "pirateforce_foundation.runtime",
        "pirateforce_foundation.store",
        "pirateforce_foundation.legacy_bridge",
    ):
        origin = Path(sys.modules[module].__file__).resolve()
        if not str(origin).startswith(home + "/") and not str(
            origin
        ).startswith(home + "\\"):
            raise RuntimeError(
                "%s came from %s, not from %s" % (module, origin, home)
            )


_refuse_a_foreign_checkout()

TOKEN_PREFIX = "LEARN_SKILL_REQUEST_ARMED"
SCENARIO_PATH = (
    ROOT / "scenarios" / (R.LEARN_SKILL_REQUEST_SCENARIO_ID + ".json")
)
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
DECODED_EVENT = "learn_skill_request_hypothesis_decoded_no_reply"
REFUSED_EVENT = "learn_skill_request_hypothesis_wrong_envelope_no_reply"


def _boot(store_path: Path):
    """Bring one session to selected-and-runtime-ready with the lane armed."""
    scenario = R.load_learn_skill_request_hypothesis_scenario(SCENARIO_PATH)
    legacy = load_legacy(LEGACY_PATH)
    store = SQLiteStore(store_path, ROOT / "migrations")
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
        learn_skill_request_hypothesis_scenario=scenario,
    )
    state = state_type("learn_request_arming")
    state.dispatch(legacy.parse_outer(
        legacy._synthetic_client_login_pc("learn_request_arming")))
    characters = store.list_characters(state.foundation.account_id)
    if not characters:
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        characters = store.list_characters(state.foundation.account_id)
    state.dispatch(legacy.parse_outer(
        legacy._synthetic_start_game_pc(characters[-1].selector)))
    state.runtime_ack_sent = True
    return legacy, state


LANE_EVENT_PREFIX = "learn_skill_request_hypothesis_"


def _drive(raw: bytes) -> tuple[list, list[str], tuple | None, int, bool]:
    """Dispatch RAW into a freshly armed session; report what it did.

    The returned event list is filtered to THIS LANE's events.  Other lanes
    on the same dispatch path legitimately narrate the same frame -- the walk
    path says ``vital_walk_refused_unknown_vital_id`` about 0x36AA, because
    0x36AA is not a walk vital -- and this proof is not entitled to speak for
    them.  What it IS entitled to check is that this lane emits exactly one
    event and no second one.

    The database bytes are read immediately before and after the one
    dispatch under test, so "wrote nothing" is a measurement of the file and
    not a reading of the code.
    """
    with tempfile.TemporaryDirectory() as tmp:
        store_path = Path(tmp) / "learn_request_arming.sqlite3"
        legacy, state = _boot(store_path)
        before = store_path.read_bytes()
        state.events.clear()
        actions = state.dispatch(legacy.parse_outer(raw))
        after = store_path.read_bytes()
    return (
        actions,
        [
            event for event in state.events
            if event.startswith(LANE_EVENT_PREFIX)
        ],
        state.learn_skill_request_last_fields,
        state.learn_skill_request_accepted_count,
        before == after,
    )


def prove_one_probe(label: str) -> str:
    """Drive one pinned probe pair through the armed dispatcher."""
    fields = R.LEARN_SKILL_REQUEST_PROBE_FIELDS[label]
    legacy = load_legacy(LEGACY_PATH)
    raw = R.compose_learn_skill_request_probe_pc(legacy, fields)
    if len(raw) != R.LEARN_SKILL_REQUEST_PROBE_REQUEST_PC_SIZE[label]:
        raise RuntimeError("probe pc size drift for %s" % label)
    actions, events, recorded, count, db_same = _drive(raw)
    if actions:
        raise RuntimeError(
            "decode-only lane emitted %d actions" % len(actions)
        )
    if events != [DECODED_EVENT]:
        raise RuntimeError("unexpected lane events %s" % ascii(events))
    if recorded != (fields.request_u32_0x14, fields.request_u8_0x18):
        raise RuntimeError("recorded %s" % ascii(recorded))
    if count != 1:
        raise RuntimeError("accepted count %d" % count)
    if not db_same:
        raise RuntimeError("the decode-only lane changed the database")
    return (
        "%s case=probe_%s actions=0 event=%s u32=%d u8=%d db_unchanged=yes"
        % (
            TOKEN_PREFIX, label, DECODED_EVENT,
            fields.request_u32_0x14, fields.request_u8_0x18,
        )
    )


def prove_the_real_capture() -> str:
    """Drive ka1-A's real captured frame #70 through the armed dispatcher.

    The expected outcome is a REFUSAL, and that is the point: the lane must
    say out loud, on a real boot, that the envelope a real client actually
    used is not the one it accepts.  A token claiming acceptance here would
    be a token nobody could reproduce at the game client.
    """
    raw = bytes.fromhex(R.LEARN_SKILL_REQUEST_REAL_CAPTURE_RAW_FRAME_HEX)
    if len(raw) != 150:
        raise RuntimeError("pinned real frame is %d bytes" % len(raw))
    actions, events, recorded, count, db_same = _drive(raw)
    if actions:
        raise RuntimeError("a refused frame emitted %d actions" % len(actions))
    if events != [REFUSED_EVENT]:
        raise RuntimeError("unexpected lane events %s" % ascii(events))
    if recorded is not None or count != 0:
        raise RuntimeError("a refused frame recorded fields")
    if not db_same:
        raise RuntimeError("a refused frame changed the database")
    return (
        "%s case=real_r312_frame70 actions=0 event=%s vitals=%d "
        "second_vital=0x%04X db_unchanged=yes"
        % (
            TOKEN_PREFIX, REFUSED_EVENT,
            R.LEARN_SKILL_REQUEST_REAL_CAPTURE_VITAL_COUNT,
            R.LEARN_SKILL_REQUEST_REAL_CAPTURE_SECOND_VITAL_ID,
        )
    )


def _run_every_case() -> int:
    """Each case gets its own process: one process serves one boot."""
    cases = [["--probe", label] for label in R.LEARN_SKILL_REQUEST_PROBE_ORDER]
    cases.append(["--real"])
    for argv in cases:
        # Address the child by FILE, not by "-m <module>": the documented
        # command has to run from a plain checkout with no PYTHONPATH set
        # (NOW.md has ka1-A re-run this proof before an attended boot and cull
        # the ticket when it does not reproduce), and "-m" needs src on the
        # path before the interpreter can find this module at all.
        done = subprocess.run(
            [sys.executable, str(_THIS_FILE)] + argv,
            capture_output=True, text=True, cwd=str(ROOT),
        )
        sys.stdout.write(done.stdout)
        sys.stderr.write(done.stderr)
        if done.returncode != 0:
            print("%s_SUMMARY probes=0 RESULT=FAIL case=%s"
                  % (TOKEN_PREFIX, " ".join(argv)))
            return 1
    print(
        "%s_SUMMARY probes=%d decoded_no_reply=yes real_frame=refused "
        "no_db_write=yes RESULT=PASS"
        % (TOKEN_PREFIX, len(R.LEARN_SKILL_REQUEST_PROBE_ORDER))
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--probe" in argv:
        print(prove_one_probe(argv[argv.index("--probe") + 1]))
        return 0
    if "--real" in argv:
        print(prove_the_real_capture())
        return 0
    return _run_every_case()


if __name__ == "__main__":
    raise SystemExit(main())
