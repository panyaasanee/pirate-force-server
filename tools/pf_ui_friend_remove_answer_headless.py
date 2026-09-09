"""ARMING PROOF: the remove-friend button is answered on a default boot.

Run it and read one line:

    UI_FRIEND_REMOVE_ANSWER_ARMED answered=1
    label=UI_FRIEND_REMOVE_ANSWERED payload_bytes=20 frame_bytes=52
    frame_matches=1 echo_is_the_players_bytes=1 junk_refused=1
    width_is_enforced=1 own_width_is_read=1 head=<12hex> code=<12hex>
    RESULT=PASS

Same shape, same rules and the same reason as the three proofs beside
it, for ``Community_RemoveFriendVital`` (``0x98A1``): a real boot with
NO flag and NO scenario, a real frame in, the frame that comes back
compared against one built independently by
``legacy.make_runtime_vitals``, and negative controls in the SAME boot.

WHY IT EXISTS AT ALL: pf-adversary round `ncejt8`, F12.  Each of the two
fixed-shape answerers before this one ships an arming proof, this one
shipped none, and without a proof there is no ``HEADLESS_PROOF:`` token,
and without that token the attended ticket for this button cannot board
the capture bus.

TWO ENFORCEMENT FIELDS, NOT ONE, and the second is this file's own
addition rather than a copy:

- ``width_is_enforced`` measures the SEAM's number the way round
  m54yxh D3 forced: not "does the encoder emit 20" (a fact about the
  encoder, true whether or not the answerer enforces anything -- the
  version of this check that could not fail) but "widen the reviewed
  row inside this boot, press again, get nothing; restore, press, get
  an answer".
- ``own_width_is_read`` measures the MODULE's number, which is round
  m54yxh D7's lesson and pf-adversary round `ncejt8` F4's finding: an
  answerer that compares only against the registry leaves its own
  constant dead, so this field moves ``_REMOVE_FRIEND_PAYLOAD_BYTES``
  alone, with the row untouched, and requires a refusal.

WHAT IT SAYS.  On this commit, on a default boot, a remove-friend frame
is ANSWERED with the player's own bytes, in the envelope this project
already ships, under a label the outbound frame-shape registry names for
this id -- so it passes the send-point gate rather than going around it.

WHAT IT DOES NOT SAY.  What the real client DRAWS, and -- unlike the
three proofs beside it -- not even that the shipped client's
"remove friend" button emits this id: ``RE-312`` nonclaim 2 records
``observed_frames = 0`` for all eight classes in both directions and
nonclaim 4 declines to claim direction.  Its handler is proven to exist
(RESULT-1, ``0x00645BF0``) and the ordinary receive path is proven to
reach the slot (RESULT-2, ``0x005F38B2``); BUILD_IMPACT 3 says the five
``Community_`` ids split INSIDE ``0x0063F9B0`` and nobody has read that
function.  All three sentences are the attended ticket's business.

WHY IT LIVES IN ``tools/``.  Same reason as its siblings: a
``make_runtime_vitals`` call inside ``src/`` moves the
``SRC_VITAL_STREAM_SITES`` census pin, and that census is a shared
instrument under repair by chief.

ASCII only, on stdout, for the cp874 bridge console.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:  # pragma: no cover - script entry
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_dispatch
from pirateforce_foundation import ui_friend_wire as wire
from pirateforce_foundation.lane_hooks import (
    lane_ui_friend_remove_answer as answerer_module,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

TOKEN = "UI_FRIEND_REMOVE_ANSWER_ARMED"
LABEL = "UI_FRIEND_REMOVE_ANSWERED"


def _synthetic_pc(legacy, nested_id: int, payload: bytes) -> bytes:
    """The outer envelope every sibling dispatch proof builds, unchanged."""
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 0x02)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, nested_id)
        + legacy.u8tag(0x0B, 0)
        + payload
    )


def _head() -> str:
    """Twelve hex of HEAD, or zeros.  A POINTER, never the verdict.

    It cannot see an edit that is not committed, which is exactly why
    ``code=`` below is the field a re-run compares.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except Exception:  # pragma: no cover - git absent
        return "0" * 12
    value = out.stdout.strip()
    return value[:12] if len(value) >= 12 else "0" * 12


def _code() -> str:
    """Twelve hex over the bytes of every ``pirateforce_foundation``
    module this proof actually imported, read from ``sys.modules``.

    This is the field ka1-A compares before a boot: it moves when the
    code under the proof moves, whether or not anything was committed.
    """
    digest = hashlib.sha256()
    for name in sorted(sys.modules):
        if not name.startswith("pirateforce_foundation"):
            continue
        path = getattr(sys.modules[name], "__file__", None)
        if not path:
            continue
        try:
            digest.update(Path(path).read_bytes())
        except OSError:  # pragma: no cover - unreadable module file
            continue
    return digest.hexdigest()[:12]


def _width_is_enforced(press) -> int:
    """Does the SEAM's reviewed number actually refuse, on this boot?

    Widen the row (the permissive edit ``!=`` exists to catch), press,
    require nothing back; restore, press, require an answer.  The row is
    restored in a ``finally``: a proof that leaves the registry it
    borrowed in a different state than it found it would be reporting on
    a server nobody is going to run.
    """
    shape = ui_dispatch.outbound_shape(LABEL)
    if shape is None:
        return 0
    try:
        ui_dispatch._OUTBOUND_FRAME_SHAPES[LABEL] = shape._replace(
            max_payload_bytes=shape.max_payload_bytes + 1
        )
        refused = press() == []
    finally:
        ui_dispatch._OUTBOUND_FRAME_SHAPES[LABEL] = shape
    return int(refused and len(press()) == 1)


def _own_width_is_read(press) -> int:
    """Does the MODULE's own number get read, or is it dead?

    Move ``_REMOVE_FRIEND_PAYLOAD_BYTES`` alone, leave the reviewed row
    where it is, and require the button to refuse.  Measured on the
    sibling class in round m54yxh: comparing only against the registry
    left the module constant at 999 with the button still working.
    """
    real = answerer_module._REMOVE_FRIEND_PAYLOAD_BYTES
    try:
        answerer_module._REMOVE_FRIEND_PAYLOAD_BYTES = real + 1
        refused = press() == []
    finally:
        answerer_module._REMOVE_FRIEND_PAYLOAD_BYTES = real
    return int(refused and len(press()) == 1)


def run() -> int:
    legacy = load_legacy(LEGACY_PATH)
    with tempfile.TemporaryDirectory() as tmp:
        store = SQLiteStore(Path(tmp) / "state.sqlite3", ROOT / "migrations")
        store.migrate()
        projector = LegacyProjector(legacy)
        lifecycle = CharacterLifecycle(
            store,
            Position(
                1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                legacy.V135_PLAYER_Z,
            ),
            legacy.extract_avatar_attr_wire_from_actor,
        )
        state_type = make_state_class(legacy, lifecycle, projector)
        state = state_type("ui-friend-remove-armed")
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc("ui-friend-remove-armed")
        ))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = store.list_characters(state.foundation.account_id)[-1]
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(character.selector)
        ))

        payload = wire.encode_remove_friend_payload(
            wire.RemoveFriendFields(
                field1_u64=0x1122334455667788,
                field2_u64=0x99AABBCCDDEEFF00,
                field3_u8=1,
            )
        )
        vital_id = wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID
        actions = state.dispatch(legacy.parse_outer(
            _synthetic_pc(legacy, vital_id, payload)
        ))
        # TWO NEGATIVE CONTROLS, NAMED FOR THE GUARD THAT REALLY REFUSES
        # THEM.  The first payload cannot decode at all; the second is a
        # whole valid payload plus one unexplained byte, which
        # ``require_exhausted`` refuses one guard before the round trip
        # and two before the width check.  Neither is evidence about the
        # width pin -- the two enforcement fields below measure that.
        junk = state.dispatch(legacy.parse_outer(
            _synthetic_pc(legacy, vital_id, b"\x00\x01\x99")
        ))
        trailer = state.dispatch(legacy.parse_outer(
            _synthetic_pc(legacy, vital_id, payload + b"\xAA")
        ))

        answered = len(actions)
        label = actions[0][0] if answered else "<none>"
        pc = actions[0][1] if answered else b""
        frame = actions[0][2] if answered else b""
        expected_pc, expected_frame = legacy.make_runtime_vitals(
            [(vital_id, wire.COMMUNITY_REMOVE_FRIEND_VITAL_VERSION, payload)]
        )
        frame_matches = int(
            bool(frame) and frame == expected_frame
            and pc == expected_pc and frame == legacy.frame_pc(pc)
        )
        # STRUCTURAL, NOT ``in``: build the SAME envelope around a marker
        # payload of the same length and require that the payload slot
        # holds exactly the player's bytes while every byte outside it is
        # the envelope's own.
        marker = b"\xEE" * len(payload)
        probe_pc, _probe_frame = legacy.make_runtime_vitals(
            [(vital_id, wire.COMMUNITY_REMOVE_FRIEND_VITAL_VERSION, marker)]
        )
        slot = probe_pc.find(marker)
        echo_exact = int(
            bool(pc)
            and slot >= 0
            and len(pc) == len(probe_pc)
            and pc[slot:slot + len(payload)] == payload
            and pc[:slot] == probe_pc[:slot]
            and pc[slot + len(payload):] == probe_pc[slot + len(payload):]
        )
        junk_refused = int(junk == [] and trailer == [])

        def _press():
            return state.dispatch(legacy.parse_outer(
                _synthetic_pc(legacy, vital_id, payload)
            ))

        # AFTER the measurements above, never before: these calls spend
        # the session's allowance, and a proof that changed the state it
        # is measuring would be reporting on a different boot than the
        # one it described.  Five presses at most, against 32.
        width_enforced = _width_is_enforced(_press)
        own_width_read = _own_width_is_read(_press)
        ok = (
            answered == 1 and label == LABEL and frame_matches
            and echo_exact and junk_refused and width_enforced
            and own_width_read
        )
        print(
            "%s answered=%d label=%s payload_bytes=%d frame_bytes=%d"
            " frame_matches=%d echo_is_the_players_bytes=%d junk_refused=%d"
            " width_is_enforced=%d own_width_is_read=%d head=%s code=%s"
            " RESULT=%s"
            % (TOKEN, answered, label, len(payload), len(frame),
               frame_matches, echo_exact, junk_refused, width_enforced,
               own_width_read, _head(), _code(), "PASS" if ok else "FAIL")
        )
        return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - entry
    return run()


if __name__ == "__main__":  # pragma: no cover - entry
    raise SystemExit(main())
