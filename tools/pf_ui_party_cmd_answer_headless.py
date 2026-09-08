"""ARMING PROOF: the party-command button is answered on a default boot.

Run it and read one line:

    UI_PARTY_CMD_ANSWER_ARMED answered=1 label=UI_PARTY_CMD_ANSWERED
    payload_bytes=11 frame_bytes=43 frame_matches=1
    echo_is_the_players_bytes=1 junk_refused=1 width_is_enforced=1
    RESULT=PASS

Same shape, same rules and the same reason as the two proofs beside it
(``src/pirateforce_foundation/ui_party_invite_answer_headless.py`` and
``tools/pf_ui_trade_invite_answer_headless.py``), for the third of the
eight vitals: a real boot with NO flag and NO scenario, a real
``PartyCmdVital`` frame in, the frame that comes back compared against
one built independently by ``legacy.make_runtime_vitals``, and negative
controls in the SAME boot -- a malformed payload must still be answered
with nothing, because a token that says PASS for everything is not
evidence.

ONE FIELD THIS CLASS'S PROOF HAS AND THE OTHER TWO DO NOT:
``width_is_enforced``.  ``PartyCmdVital`` is ``u8 + u64`` with no
string, so its payload cannot vary, and the reviewed outbound shape
pins the EXACT width rather than a ceiling.

ITS FIRST VERSION WAS CALLED ``width_is_fixed`` AND COULD NOT FAIL
(pf-adversary round m54yxh, D3).  It asked whether the encoder emits
the reviewed number for four field extremes -- a fact about the encoder
and a literal, true whether or not the answerer enforces anything, so
deleting the whole width guard left this proof printing PASS with exit
0.  A proof that cannot fail when the feature is removed is not
evidence of the feature.  It now MEASURES THE ENFORCEMENT: inside the
same boot it widens the reviewed row (the permissive edit, the one
``!=`` exists to catch), presses the button again, and requires the
answer to be nothing; then restores the row and requires the button to
work again.  Delete the guard and this field reads 0 and the token says
FAIL.

WHAT IT SAYS.  On this commit, on a default boot, a party-command frame
is ANSWERED, with the player's own bytes, in the envelope this project
already ships, under a label the outbound frame-shape registry names for
this id (COO-DECISION 20260908_1142 item 7 route (b)) -- so it passes
the send-point gate rather than going around it.

WHAT IT DOES NOT SAY.  What the real client DRAWS when it receives that
frame.  ``RE-312`` RESULT-1 proves a live inbound handler exists at
``0x0062EA70`` and RESULT-2 that the ordinary receive path reaches it;
RE-312's own nonclaim 2 records ``observed_frames = 0``.  That is the
attended ticket's question, and this file exists to stop that ticket
boarding the capture bus blind.

WHY IT LIVES IN ``tools/``.  Not to dodge a guard: a ``make_runtime_vitals``
call inside ``src/`` moves the ``SRC_VITAL_STREAM_SITES`` census pin,
and that census is a SHARED instrument whose own blind spot is under
repair by chief right now (COO-DECISION ``20260908_1441`` item 2 -- it
reads 32 where the truth is 38).  Moving another lane's pin while its
owner is mid-repair buys a green suite by making somebody else's
measurement wronger.  An arming proof is a script, so it sits with the
other proof scripts and the census is left alone.

ASCII only, on stdout, for the cp874 bridge console.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:  # pragma: no cover - script entry
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_dispatch
from pirateforce_foundation import ui_party_wire as wire
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

TOKEN = "UI_PARTY_CMD_ANSWER_ARMED"
LABEL = "UI_PARTY_CMD_ANSWERED"


def _synthetic_pc(legacy, nested_id: int, payload: bytes) -> bytes:
    """The outer envelope both dispatch test files build, unchanged."""
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


def _width_is_enforced(press) -> int:
    """Does the fixed-width guard actually refuse, on this boot?

    ``press`` sends one well-formed party command through the real
    dispatcher and returns the actions.  Two halves, and BOTH have to
    hold:

    1. every field extreme encodes to the reviewed width (a fact about
       the encoder and the reviewed literal -- necessary, and on its own
       it was the whole of this check, which is why deleting the guard
       used to leave this proof green);
    2. with the reviewed row WIDENED by one byte, the same press answers
       NOTHING, and with the row restored it answers again.  That is the
       guard executing, on the live path, in this boot.

    The row is restored in a ``finally``: a proof that leaves the
    registry it borrowed in a different state than it found it would be
    reporting on a server nobody is going to run.
    """
    shape = ui_dispatch.outbound_shape(LABEL)
    if shape is None:
        return 0
    widths = {
        len(wire.encode_party_cmd_payload(
            wire.PartyCmdFields(field1_u8=a, field2_u64=b)
        ))
        for a in (0, 0xFF)
        for b in (0, (1 << 64) - 1)
    }
    if widths != {shape.max_payload_bytes}:
        return 0
    try:
        ui_dispatch._OUTBOUND_FRAME_SHAPES[LABEL] = shape._replace(
            max_payload_bytes=shape.max_payload_bytes + 1
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
        state = state_type("ui-party-cmd-armed")
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc("ui-party-cmd-armed")
        ))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = store.list_characters(state.foundation.account_id)[-1]
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(character.selector)
        ))

        payload = wire.encode_party_cmd_payload(
            wire.PartyCmdFields(field1_u8=1, field2_u64=0x1122334455667788)
        )
        actions = state.dispatch(legacy.parse_outer(
            _synthetic_pc(legacy, wire.PARTY_CMD_VITAL_ID, payload)
        ))
        # TWO NEGATIVE CONTROLS, NOT ONE, AND THE SECOND IS NAMED FOR
        # THE GUARD THAT REALLY REFUSES IT (pf-adversary round m54yxh,
        # D6 -- this comment used to say the trailer "decodes
        # field-for-field" and is caught by the fixed width, and the
        # proof's own stderr says otherwise: ``reason=undecodable``).
        # The first payload cannot decode at all; the second is a whole
        # valid payload plus one unexplained byte, which
        # ``require_exhausted`` refuses one guard before the round trip
        # and two before the width check.  Both are evidence that a
        # malformed press is answered with nothing -- not evidence about
        # the width pin, which ``width_is_enforced`` below measures on
        # its own.
        junk = state.dispatch(legacy.parse_outer(
            _synthetic_pc(legacy, wire.PARTY_CMD_VITAL_ID, b"\x00\x01\x99")
        ))
        trailer = state.dispatch(legacy.parse_outer(
            _synthetic_pc(legacy, wire.PARTY_CMD_VITAL_ID, payload + b"\xAA")
        ))

        answered = len(actions)
        label = actions[0][0] if answered else "<none>"
        pc = actions[0][1] if answered else b""
        frame = actions[0][2] if answered else b""
        expected_pc, expected_frame = legacy.make_runtime_vitals(
            [(wire.PARTY_CMD_VITAL_ID,
              wire.PARTY_CMD_VITAL_VERSION, payload)]
        )
        frame_matches = int(
            bool(frame) and frame == expected_frame
            and pc == expected_pc and frame == legacy.frame_pc(pc)
        )
        # STRUCTURAL, NOT ``in`` (pf-adversary round xqxadg, D10): build
        # the SAME envelope around a marker payload of the same length
        # and require that the payload slot holds exactly the player's
        # bytes while every byte outside it is the envelope's own.
        marker = b"\xEE" * len(payload)
        probe_pc, _probe_frame = legacy.make_runtime_vitals(
            [(wire.PARTY_CMD_VITAL_ID, wire.PARTY_CMD_VITAL_VERSION, marker)]
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
                _synthetic_pc(legacy, wire.PARTY_CMD_VITAL_ID, payload)
            ))

        # AFTER the measurements above, never before: this call spends
        # the session's allowance, and a proof that changed the state it
        # is measuring would be reporting on a different boot than the
        # one it described.  Three presses at most, against an allowance
        # of 32.
        width_enforced = _width_is_enforced(_press)
        ok = (
            answered == 1 and label == LABEL and frame_matches
            and echo_exact and junk_refused and width_enforced
        )
        print(
            "%s answered=%d label=%s payload_bytes=%d frame_bytes=%d"
            " frame_matches=%d echo_is_the_players_bytes=%d junk_refused=%d"
            " width_is_enforced=%d RESULT=%s"
            % (TOKEN, answered, label, len(payload), len(frame),
               frame_matches, echo_exact, junk_refused, width_enforced,
               "PASS" if ok else "FAIL")
        )
        return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - entry
    return run()


if __name__ == "__main__":  # pragma: no cover - entry
    raise SystemExit(main())
