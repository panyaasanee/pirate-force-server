"""ARMING PROOF: the trade-invite button is answered on a default boot.

Run it and read one line:

    UI_TRADE_INVITE_ANSWER_ARMED answered=1 label=UI_TRADE_INVITE_ANSWERED
    frame_bytes=58 frame_matches=1 echo_is_the_players_bytes=1
    junk_refused=1 RESULT=PASS

Same shape, same rules and the same reason as the party proof beside
this file (``ui_party_invite_answer_headless.py``), for the second of
the eight vitals: a real boot with NO flag and NO scenario, a real
``TradeInviteVital`` frame in, the frame that comes back compared
against one built independently by ``legacy.make_runtime_vitals``, and a
negative control -- a malformed payload in the SAME boot must still be
answered with nothing, because a token that says PASS for everything is
not evidence.

WHAT IT SAYS.  On this commit, on a default boot, a trade-invite frame
is ANSWERED, with the player's own bytes, in the envelope this project
already ships, and the reply carries a label the outbound frame-shape
registry names for this id (COO-DECISION 20260908_1142 item 7 route
(b)) -- so it passes the send-point gate rather than going around it.

WHAT IT DOES NOT SAY.  What the real client DRAWS when it receives that
frame.  RE-312 proves a live inbound handler exists and that the
ordinary receive path reaches it; its own nonclaim 2 records
``observed_frames = 0`` -- nobody has measured these handlers at
runtime.  That is the attended ticket's question, and this file exists
to stop that ticket boarding the capture bus blind.

WHY THIS ONE LIVES IN ``tools/`` AND THE PARTY PROOF LIVES IN ``src/``.
``tests/test_npc_interaction_wire.py::QuestAndShopStateGuardTests`` reads
every top-level module of ``src/pirateforce_foundation`` and refuses
identifiers carrying trade/shop/quest vocabulary, so that no foundation
module quietly grows shop behaviour.  This proof has to spell
``encode_trade_invite_payload`` to build a real payload, and the honest
way past a guard is not to be exempted from it: the guard's subject is
FOUNDATION MODULES, and an arming proof is a script.  So it sits with
the other proof scripts instead of asking for an allowlist entry in
another lane's guard (NOW `2050` forbids exactly that trade).  The
consequence is recorded, not hidden: this file's ``make_runtime_vitals``
calls are outside ``src/`` and therefore outside the
``SRC_VITAL_STREAM_SITES`` census, which is why that pin reads 32 and
not 34.

ASCII only, on stdout, for the cp874 bridge console.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:  # pragma: no cover - script entry
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_trade_wire as wire
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

TOKEN = "UI_TRADE_INVITE_ANSWER_ARMED"


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
        state = state_type("ui-trade-armed")
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc("ui-trade-armed")
        ))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = store.list_characters(state.foundation.account_id)[-1]
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(character.selector)
        ))

        payload = wire.encode_trade_invite_payload(
            wire.TradeInviteFields(
                field1_u8=1, field2_u64=0x1122334455667788,
                field3_wstring="Panya",
            )
        )
        actions = state.dispatch(legacy.parse_outer(
            _synthetic_pc(legacy, wire.TRADE_INVITE_VITAL_ID, payload)
        ))
        junk = state.dispatch(legacy.parse_outer(
            _synthetic_pc(legacy, wire.TRADE_INVITE_VITAL_ID, b"\x00\x01\x99")
        ))

        answered = len(actions)
        label = actions[0][0] if answered else "<none>"
        pc = actions[0][1] if answered else b""
        frame = actions[0][2] if answered else b""
        expected_pc, expected_frame = legacy.make_runtime_vitals(
            [(wire.TRADE_INVITE_VITAL_ID,
              wire.TRADE_INVITE_VITAL_VERSION, payload)]
        )
        frame_matches = int(
            bool(frame) and frame == expected_frame
            and pc == expected_pc and frame == legacy.frame_pc(pc)
        )
        # ``in`` WAS A SUBSTRING TEST (pf-adversary round xqxadg, D10).
        # The field is read as "the payload that went back is
        # byte-identical to the one that came in", and containment does
        # not say that: a reply of ``payload + b"\xAA"`` satisfied it
        # while inventing a byte.  ``endswith`` is wrong too -- this
        # envelope puts two bytes after the nested payload.  So the
        # check is structural and does not lean on the comparison
        # ``frame_matches`` already makes: build the SAME envelope
        # around a marker payload of the same length, and require that
        # the bytes in the payload slot are exactly the player's while
        # every byte outside it is the envelope's own.
        marker = b"\xEE" * len(payload)
        probe_pc, _probe_frame = legacy.make_runtime_vitals(
            [(wire.TRADE_INVITE_VITAL_ID, wire.TRADE_INVITE_VITAL_VERSION, marker)]
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
        junk_refused = int(junk == [])
        ok = answered == 1 and frame_matches and echo_exact and junk_refused
        print(
            "%s answered=%d label=%s frame_bytes=%d frame_matches=%d"
            " echo_is_the_players_bytes=%d junk_refused=%d RESULT=%s"
            % (TOKEN, answered, label, len(frame), frame_matches,
               echo_exact, junk_refused, "PASS" if ok else "FAIL")
        )
        return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - entry
    return run()


if __name__ == "__main__":  # pragma: no cover - entry
    raise SystemExit(main())
