"""Arming proof for the first UI vital the server ever answers.

Why this file exists
--------------------
``NOW.md`` (PANYA ``0159`` / ``2148``) requires every attended ticket to
carry a ``HEADLESS_PROOF:`` line: a console token from a headless run on
the current ``main`` commit showing that the mechanism the ticket is
about is ARMED on a default, flagless boot, plus a token saying the
server actually sent something.  ``GT-178``'s R322C boot is the reason --
a tester spent an attended slot discovering that scene 14 had no tick,
which one console line would have told them for free.

This module is that line for ``PartyInviteVital`` (``0x37B1``).  It boots
the REAL dispatcher (``make_state_class`` with no scenario) on a
throwaway database, logs in, creates and starts a character exactly as a
player's client does, then drives ONE real party-invite frame through
``state.dispatch`` and measures:

  * an action comes back at all -- the branch that returned ``[]`` for
    every one of the eight UI vitals now answers this one;
  * the frame in that action is byte-identical to the one
    ``legacy.make_runtime_vitals`` builds independently from the id,
    version and payload that arrived, and to ``legacy.frame_pc(pc)``;
  * the payload that goes back is byte-identical to the payload that
    came in, so no field was invented;
  * a malformed invite in the same boot is still answered with nothing,
    so the token is not reporting a branch that answers everything.

What the token is entitled to say, and what it is not
-----------------------------------------------------
It says: on this commit, on a default boot with no flag and no scenario,
a real party-invite frame is ANSWERED by the server, with the player's
own bytes, and the frame is the envelope this project already ships.

It does NOT say what the real client DRAWS when it receives that frame.
RE-312 (pf_bridge ``notes_to_chief/20260908_1038_*`` and
``20260908_1105_*``) proves the client has a live inbound handler for
this class and that the ordinary receive path reaches it; it proves
nothing about pixels, and its own nonclaim 2 says no one has measured
these handlers at runtime.  That is the attended ticket's question, and
this file exists to stop that ticket boarding the capture bus blind.

ASCII only, on stdout, for the cp874 bridge console.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:  # pragma: no cover - script entry
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_party_wire as wire
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

TOKEN = "UI_PARTY_INVITE_ANSWER_ARMED"


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
        state = state_type("ui-party-armed")
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc("ui-party-armed")
        ))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = store.list_characters(state.foundation.account_id)[-1]
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(character.selector)
        ))

        payload = wire.encode_party_invite_payload(
            wire.PartyInviteFields(
                field1_u8=1, field2_u64=0x1122334455667788,
                field3_wstring="Panya",
            )
        )
        actions = state.dispatch(legacy.parse_outer(
            _synthetic_pc(legacy, wire.PARTY_INVITE_VITAL_ID, payload)
        ))
        junk = state.dispatch(legacy.parse_outer(
            _synthetic_pc(legacy, wire.PARTY_INVITE_VITAL_ID, b"\x00\x01\x99")
        ))

        answered = len(actions)
        label = actions[0][0] if answered else "<none>"
        pc = actions[0][1] if answered else b""
        frame = actions[0][2] if answered else b""
        expected_pc, expected_frame = legacy.make_runtime_vitals(
            [(wire.PARTY_INVITE_VITAL_ID,
              wire.PARTY_INVITE_VITAL_VERSION, payload)]
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
            [(wire.PARTY_INVITE_VITAL_ID, wire.PARTY_INVITE_VITAL_VERSION, marker)]
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
