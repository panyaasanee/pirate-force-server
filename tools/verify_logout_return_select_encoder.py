#!/usr/bin/env python3
"""LOGOUT-RETURN-SELECT-001: offline verifier for HYP-PF-028 (GT-033 B).

WHAT THIS PROVES, and where the proof stops
-------------------------------------------
That the return-select logout lane composes EXACTLY one well-formed
ReturnSelectServerVital (0x709E) response whose 16-byte body is the client
serializer 0x5e69f0's own field layout with every field zero, wraps it in the
accepted GSCN_RunTimeProtocolRes v4 envelope, keeps the PF-012 ack bytes and
the PF-013 clean close byte-identical, and refuses -- by name and with no
bytes -- every scenario the exact allowlist can drive wrong.  An independent
walker in this file reads the 16-byte body back tag by tag (0x08 u8, 0x32
8-byte scalar, 0x44 empty std::string) rather than trusting the module.

It proves NOTHING about a client.  No client has ever been shown one byte of
this profile; whether the real client transitions to character select on
0x709E is GT-033 (attended, not run).  Round-100 static RE (agent D) proved an
ECHO cannot transition the client (the inbound 0x446F30 reconcile pass never
switches scene/state/connection) and named 0x709E the strongest candidate for
the char-select direction while finding no client code that consumes it -- so
the response we send is OUR design; the original server's return-select
response is unknown and unrecoverable.

DISCIPLINE
----------
Pure stdlib plus the frozen v141 legacy module for composition only.  No
server process, no socket, no database, no client, no GameClient window, no
repository write.

Usage:
    py -3 tools/verify_logout_return_select_encoder.py

Exit 0 = every guard held.  Exit 1 = at least one drifted, with the list.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import logout_hypothesis as L  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
RETURN_SELECT_SCENARIO = (
    ROOT / "scenarios" / "logout_hypothesis_return_select_server.json"
)
ECHO_SCENARIO = ROOT / "scenarios" / "logout_hypothesis_ack_echo.json"
CLOSE_SCENARIO = ROOT / "scenarios" / "logout_hypothesis_ack_close.json"

# ---------------------------------------------------------------------------
# This reader's own constants, written as literals so section A measures the
# module against THEM.  These are the round-101 static decode results of the
# client serializer 0x5e69f0 (descriptor table 0xf304ec slot2).
# ---------------------------------------------------------------------------
RSS_VITAL_ID = 0x709E
RUNTIME_PROTOCOL_RES_ID = 0x6E9D
FIELD1_TAG = 0x08          # u8
FIELD2_TAG = 0x32          # 8-byte scalar
FIELD3_TAG = 0x44          # std::string (u32 length + data)
BODY_HEX = "08003200000000000000004400000000"
BODY_SIZE = 16
RESP_PC_SIZE = 38
RESP_FRAME_SIZE = 48
RESP_PC_SHA = "A4C8DF4299EA7C3A5EE5554D1D29D7F8C1A2B51031CA210CBEB9AF2AD9D4CA9E"
RESP_FRAME_SHA = (
    "08C2A925BD67CD3D0AFA7992F98D472ED8FD22787756521A5DF8CBF174E5CB8E"
)

failures: list[str] = []
guards = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global guards
    guards += 1
    if condition:
        print("  PASS  %s" % label)
    else:
        failures.append(label)
        print("  FAIL  %s %s" % (label, detail))


def reject(label: str, thunk, needle: str = "") -> None:
    """The named-refusal driver: the call must raise, optionally saying why."""
    global guards
    guards += 1
    try:
        thunk()
    except (ValueError, RuntimeError) as exc:
        if needle and needle not in str(exc):
            failures.append(label)
            print("  FAIL  %s wrong refusal: %s" % (label, ascii(str(exc))))
            return
        print("  PASS  %s" % label)
        return
    failures.append(label)
    print("  FAIL  %s did not refuse at all" % label)


def walk_body(body: bytes) -> dict:
    """Read the 16-byte ReturnSelectServerVital body by hand, byte zero on."""
    if len(body) != BODY_SIZE:
        raise ValueError("body length %d != %d" % (len(body), BODY_SIZE))
    cur = 0
    if body[cur] != FIELD1_TAG:
        raise ValueError("field1 tag 0x%02X != 0x08" % body[cur])
    field1 = body[cur + 1]
    cur += 2
    if body[cur] != FIELD2_TAG:
        raise ValueError("field2 tag 0x%02X != 0x32" % body[cur])
    field2 = int.from_bytes(body[cur + 1:cur + 9], "little")
    cur += 9
    if body[cur] != FIELD3_TAG:
        raise ValueError("field3 tag 0x%02X != 0x44" % body[cur])
    length = int.from_bytes(body[cur + 1:cur + 5], "little")
    cur += 5
    string = body[cur:cur + length]
    cur += length
    if cur != len(body):
        raise ValueError("reader accounted for %d of %d" % (cur, len(body)))
    return {"field1": field1, "field2": field2, "strlen": length,
            "string": string}


def main() -> int:
    legacy = load_legacy(LEGACY_PATH)
    scenario = L.load_logout_hypothesis_scenario(RETURN_SELECT_SCENARIO)
    pinned = json.loads(RETURN_SELECT_SCENARIO.read_text(encoding="utf-8"))

    print("-- A. this reader's constants against the module's --")
    check("the vital id is 0x709E on both sides",
          RSS_VITAL_ID == L.RETURN_SELECT_SERVER_VITAL_ID == 0x709E)
    check("the module body equals this reader's literal, 16 bytes",
          L.RETURN_SELECT_SERVER_BODY == bytes.fromhex(BODY_HEX)
          and len(L.RETURN_SELECT_SERVER_BODY) == BODY_SIZE
          and L.RETURN_SELECT_SERVER_BODY_SIZE == BODY_SIZE)
    check("the composed-response sizes and hashes agree with the module",
          RESP_PC_SIZE == L.RETURN_SELECT_SERVER_RESPONSE_PC_SIZE
          and RESP_FRAME_SIZE == L.RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE
          and RESP_PC_SHA == L.RETURN_SELECT_SERVER_RESPONSE_PC_SHA256
          and RESP_FRAME_SHA == L.RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256)
    check("the response policy string agrees",
          scenario.response_policy
          == L.LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST
          == "return_select_server_first")
    check("the profile keeps the PF-013 close lever and 250 ms delay",
          scenario.post_ack_action == L.LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET
          and scenario.close_delay_ms == L.LOGOUT_CLOSE_DELAY_MS)
    check("the hypothesis id is HYP-PF-028",
          scenario.hypothesis_id == "HYP-PF-028")

    print("-- B. the 16-byte body is the client serializer's own tag layout --")
    body = L.RETURN_SELECT_SERVER_BODY
    read = walk_body(body)
    check("field1 is tag 0x08 (u8) and defaults to zero (no client producer)",
          body[0] == FIELD1_TAG and read["field1"] == 0)
    check("field2 is tag 0x32 (8-byte scalar) and defaults to zero",
          body[2] == FIELD2_TAG and read["field2"] == 0)
    check("field3 is tag 0x44 (std::string) with an empty, zero-length string",
          body[11] == FIELD3_TAG and read["strlen"] == 0
          and read["string"] == b"")
    check("every tag byte is one of the three the serializer 0x5e69f0 writes",
          set([body[0], body[2], body[11]]) == {0x08, 0x32, 0x44})

    print("-- C. the composed response, recomposed and re-pinned --")
    pc, frame = L.make_return_select_server_response(legacy)
    check("PC size and sha match the pin",
          len(pc) == RESP_PC_SIZE
          and hashlib.sha256(pc).hexdigest().upper() == RESP_PC_SHA)
    check("frame size and sha match the pin",
          len(frame) == RESP_FRAME_SIZE
          and hashlib.sha256(frame).hexdigest().upper() == RESP_FRAME_SHA)
    check("the PC opens with the RuntimeRes v4 envelope, one vital",
          pc[:15] == bytes.fromhex("129D6E140000000008040B02120100"))
    check("the nested vital id on the wire is 0x709E, version 0",
          pc[15:18] == bytes.fromhex("129E70") and pc[18:20] == b"\x0B\x00")
    check("the 16-byte body rides verbatim after the nested header",
          pc[20:20 + BODY_SIZE] == body)
    check("the PC closes with the proven trailing derived-class mask 0B 00",
          pc[-2:] == b"\x0B\x00")
    check("frame == frame_pc(pc) on the composed PC",
          frame == legacy.frame_pc(pc))
    check("the composed PC parses with the frozen v141 outer parser",
          legacy.parse_outer(pc) is not None)

    print("-- D. the ack and close levers are the unchanged PF-012/013 pins --")
    for subcode in (1, 3):
        apc, aframe = L.make_logout_ack_response(legacy, subcode)
        check("ack subcode %02d PC/frame match the PF-012 pins" % subcode,
              hashlib.sha256(apc).hexdigest().upper()
              == L.LOGOUT_ACK_PC_SHA256[subcode]
              and hashlib.sha256(aframe).hexdigest().upper()
              == L.LOGOUT_ACK_FRAME_SHA256[subcode])

    print("-- E. the exact scenario allowlist refuses every tamper --")
    check("production_allowed is false in the scenario file",
          pinned["production_allowed"] is False)
    check("test_only is true in the scenario file",
          pinned["test_only"] is True)

    def tamper(mut) -> None:
        data = json.loads(json.dumps(pinned))
        mut(data)
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8",
        ) as fh:
            fh.write(json.dumps(data))
            tmp = Path(fh.name)
        try:
            L.load_logout_hypothesis_scenario(tmp)
        finally:
            tmp.unlink()

    reject("flip production_allowed true is refused",
           lambda: tamper(lambda d: d.__setitem__("production_allowed", True)),
           "allowlist")
    reject("flip test_only false is refused",
           lambda: tamper(lambda d: d.__setitem__("test_only", False)),
           "allowlist")
    reject("swap response_policy to ack_only is refused",
           lambda: tamper(
               lambda d: d["entry"].__setitem__("response_policy", "ack_only")),
           "allowlist")
    reject("drop the close lever is refused",
           lambda: tamper(
               lambda d: d["entry"].__setitem__("post_ack_action", "none")),
           "allowlist")
    reject("widen the close delay is refused",
           lambda: tamper(
               lambda d: d["entry"].__setitem__("close_delay_ms", 5000)),
           "allowlist")
    reject("forge the composed response sha is refused",
           lambda: tamper(
               lambda d: d["composed_responses"]["return_select_first"]
               .__setitem__("pc_sha256", "00" * 32)),
           "allowlist")
    reject("forge the vital id to LogoutVital is refused",
           lambda: tamper(
               lambda d: d["composed_responses"]["return_select_first"]
               .__setitem__("vital_id", 0x1B40)),
           "allowlist")
    reject("shrink the body size is refused",
           lambda: tamper(
               lambda d: d["composed_responses"]["return_select_first"]
               .__setitem__("body_size", 2)),
           "allowlist")
    reject("an unknown scenario id object is refused by the object allowlist",
           lambda: L.require_logout_hypothesis_scenario("not a scenario"),
           "allowlist")

    print("-- F. the honest nonclaims are written on the profile --")
    nonclaims = pinned["nonclaims"]
    check("the profile disclaims the original-server response policy",
          "original_server_response_policy" in nonclaims)
    check("the profile disclaims that the client consumes 0x709E or transitions",
          "client_consumes_0x709e_or_transitions_to_character_select"
          in nonclaims)
    check("the profile disclaims the field values and string semantics",
          "return_select_server_field_values_and_string_semantics" in nonclaims)

    print()
    print("guards run: %d" % guards)
    if failures:
        print("RESULT: FAIL - %d guard(s) drifted: %s"
              % (len(failures), failures))
        return 1
    print("RESULT: PASS - the return-select lane composes one well-formed "
          "0x709E vital from the client serializer's own field layout, keeps "
          "the PF-012/013 pins, refuses every driven tamper by name, and "
          "claims nothing about a client (GT-033 is queued, not run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
