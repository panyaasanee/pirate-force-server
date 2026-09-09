"""ARMING PROOF: the add-friend button is answered on a default boot.

Run it and read one line:

    UI_FRIEND_REQUEST_ANSWER_ARMED answered=1
    label=UI_FRIEND_REQUEST_ANSWERED payload_bytes=<n> frame_bytes=<n>
    frame_matches=1 echo_is_the_players_bytes=1 junk_refused=1
    ceiling_is_enforced=1 head=<12hex> code=<12hex> RESULT=PASS

Same shape, same rules and the same reason as the proofs beside this
file, for ``Community_RequestBeFriendVital`` (``0xB9E9``): a real boot
with NO flag and NO scenario, a real frame in, the frame that comes
back compared against one built independently by
``legacy.make_runtime_vitals``, and negative controls in the SAME boot.

WHY THIS PROOF DID NOT EXIST BEFORE THIS ROUND.  The answerer module
declared ``ARMING_TOKEN``/``arming_sample()`` from the round it landed
(``asw0n3``), for a GENERALIZED runner that reads the reviewed owner
table and asks each lane for its own token -- that runner is
``pirate-force-server#1167``, still not on ``main`` as of this round.
Until it lands, this class had no standalone proof script of its own,
which is exactly the gap ``GT-318`` (party invite) is held open on:
K's own note on that ticket says nobody has re-run its proof on the
CURRENT ``main`` in this round, and the same was true of this class
with no script to run at all.  This file closes that gap the same way
the trade-invite and friend-removal proofs already did: one
class-specific script, not a wait for the generalized runner.

ONE FIELD THIS PROOF ADDS THAT THE FIXED-WIDTH PROOFS DO NOT NEED:
``ceiling_is_enforced``.  This class's reviewed row is a CEILING
(``>``), not an EQUALITY, because a name makes the payload grow -- so
the meaningful measurement is "shrink the reviewed row inside this
boot, press a payload that is now too big, get nothing; restore, press
the same payload, get an answer" (the shape round m54yxh D3 forced onto
the fixed-width proofs, adapted for a ceiling).

WHAT IT SAYS.  On this commit, on a default boot, an add-friend frame
is ANSWERED with the player's own bytes, in the envelope this project
already ships, under a label the outbound frame-shape registry names
for this id.

WHAT IT DOES NOT SAY.  What the real client DRAWS, and not that the
shipped client's "add friend" control emits this id: ``RE-312``
nonclaim 2 records ``observed_frames = 0`` for all eight classes in
both directions and nonclaim 4 declines to claim direction.  Its
handler is proven to exist (RESULT-1, ``0x00645BF0``) and the ordinary
receive path is proven to reach the slot (RESULT-2, ``0x005F38B2``);
BUILD_IMPACT 3 says the five ``Community_`` ids split INSIDE
``0x0063F9B0`` and nobody has read that function.  All three sentences
are the attended ticket's business.

WHY IT LIVES IN ``tools/`` AND NOT ``src/``.  Same reason as the
proofs beside it: a ``make_runtime_vitals`` call inside ``src/`` moves
the ``SRC_VITAL_STREAM_SITES`` census pin, a shared instrument under
repair by chief, and the honest way past another lane's guard is not to
ask for an allowlist entry in it (NOW `2050`).

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
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

TOKEN = "UI_FRIEND_REQUEST_ANSWER_ARMED"
LABEL = "UI_FRIEND_REQUEST_ANSWERED"


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
    """Twelve hex of HEAD, or zeros.  A POINTER, never the verdict."""
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
    module this proof actually imported, read from ``sys.modules``."""
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


def _ceiling_is_enforced(press, payload_len: int) -> int:
    """Does the SEAM's reviewed ceiling actually refuse, on this boot?"""
    shape = ui_dispatch.outbound_shape(LABEL)
    if shape is None:
        return 0
    try:
        ui_dispatch._OUTBOUND_FRAME_SHAPES[LABEL] = shape._replace(
            max_payload_bytes=payload_len - 1
        )
        refused = press() == []
    finally:
        ui_dispatch._OUTBOUND_FRAME_SHAPES[LABEL] = shape
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
        state = state_type("ui-friend-request-armed")
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc("ui-friend-request-armed")
        ))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = store.list_characters(state.foundation.account_id)[-1]
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(character.selector)
        ))

        payload = wire.encode_request_be_friend_payload(
            wire.RequestBeFriendFields(
                field1_u64=0x1122334455667788,
                field2_wstring="Ann",
                field3_u8=1,
            )
        )
        vital_id = wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_ID
        actions = state.dispatch(legacy.parse_outer(
            _synthetic_pc(legacy, vital_id, payload)
        ))
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
            [(vital_id, wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_VERSION,
              payload)]
        )
        frame_matches = int(
            bool(frame) and frame == expected_frame
            and pc == expected_pc and frame == legacy.frame_pc(pc)
        )
        marker = b"\xEE" * len(payload)
        probe_pc, _probe_frame = legacy.make_runtime_vitals(
            [(vital_id, wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_VERSION,
              marker)]
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

        ceiling_enforced = _ceiling_is_enforced(_press, len(payload))
        ok = (
            answered == 1 and label == LABEL and frame_matches
            and echo_exact and junk_refused and ceiling_enforced
        )
        print(
            "%s answered=%d label=%s payload_bytes=%d frame_bytes=%d"
            " frame_matches=%d echo_is_the_players_bytes=%d junk_refused=%d"
            " ceiling_is_enforced=%d head=%s code=%s RESULT=%s"
            % (TOKEN, answered, label, len(payload), len(frame),
               frame_matches, echo_exact, junk_refused, ceiling_enforced,
               _head(), _code(), "PASS" if ok else "FAIL")
        )
        return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - entry
    return run()


if __name__ == "__main__":  # pragma: no cover - entry
    raise SystemExit(main())
