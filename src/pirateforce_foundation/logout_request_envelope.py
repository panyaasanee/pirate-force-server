"""Structural (not exact-frame-hash) classifier for LogoutVital (0x1B40)
request frames -- the wire request behind UI-A ("return to character
select") and UI-B ("exit game"), both owned by LANE-A per
``FROM_CHIEF_R278`` lines 49-50.

Why this module exists
-----------------------
``logout_hypothesis.py``'s ``LOGOUT_REQUEST_PC_SHA256`` pins the two known
LogoutVital request forms as WHOLE-FRAME SHA-256 hashes, captured from a
session where the envelope carried exactly one vital (envelope vital-count
byte == 0x01, 34 bytes total: 13-byte prefix + 1 count byte + 1 reserved
byte + the 19-byte LogoutVital entry).

A fresh capture landed 2026-09-01 ~19:30 (``notes_to_chief/
20260901_1930_KA1A-CAPTURE-the-owner-clicked-both-UI-A-and-UI-B-buttons-
herself-exact-bytes-plus-a-design-problem-for-HYP-PF-040.md``): the owner
clicked BOTH real client buttons herself, once each, before closing the
client. subcode 3 ("return to character select") reproduced the existing
34-byte pin byte-for-byte -- no change needed there. subcode 1 ("exit
game") did NOT: the real client's envelope carried the LogoutVital entry
PLUS three more vitals bundled into the same frame (envelope vital-count
byte 0x04, not 0x01), extending the frame from the pinned 34 bytes to a
genuinely different, legally-valid 119 bytes.

Verified byte-for-byte (not assumed) against both the existing
``LOGOUT_REQUEST_PCS`` pins and the new capture:
  * bytes[0:13]  -- envelope prefix -- IDENTICAL regardless of subcode,
    envelope vital-count, or trailing content.
  * byte[13]     -- envelope vital-count -- the ONLY byte that differs
    between the 34-byte and 119-byte subcode-1 captures (0x01 vs 0x04).
  * byte[14]     -- reserved -- 0x00 in every capture seen so far.
  * bytes[15:34] -- the LogoutVital vital entry itself (wrapper tag, the
    vital id 0x1B40 little-endian, a fixed 2-byte span, the subcode tag
    and byte, and a fixed 12-byte payload tail) -- byte-identical whether
    LogoutVital is the ONLY vital in the envelope or the FIRST of four.
  * bytes[34:]   -- present only when the envelope carries extra vitals;
    an explicit nonclaim here (never parsed, never required, never
    invented) -- returned as-is for whichever lane eventually wants them.

A frame that matches ``LOGOUT_REQUEST_PC_SHA256`` therefore always also
classifies correctly here (checked in tests/test_logout_request_envelope.py
against the module's own pins). The reverse is not true: this classifier
recognizes the real 119-byte subcode-1 frame that the exact-hash pin
cannot, which is the likely reason UI-B ("exit game") button clicks have
not reliably been recognized by any exact-hash-keyed dispatch so far --
real button presses are not guaranteed to happen with an empty vital
queue.

This module does not touch dispatch, does not import ``runtime.py``, and
changes no composed response byte. Wiring its result into
``logout_hypothesis.py``'s request matcher is a CORE-REQUEST to chief:
that module is locked outside a one-time per-round grant (see its own
module docstring history), and this lane's write zone for THIS round is
new modules only.
"""

from __future__ import annotations

from dataclasses import dataclass


LOGOUT_VITAL_ID = 0x1B40
LOGOUT_SUBCODE_EXIT_GAME = 1
LOGOUT_SUBCODE_CHARACTER_SELECT = 3
LOGOUT_SUBCODES = (LOGOUT_SUBCODE_EXIT_GAME, LOGOUT_SUBCODE_CHARACTER_SELECT)

# bytes[0:13] -- constant across every captured LogoutVital request so far,
# independent of subcode and independent of how many other vitals ride
# along in the same envelope.
_ENVELOPE_PREFIX_13 = bytes.fromhex("126F6E140000000008000B0212")

# byte[14] -- constant 0x00 in every capture seen so far (reserved /
# padding; meaning is an explicit nonclaim of this module).
_BYTE_14_RESERVED = 0x00

# bytes[15:34] (19 bytes) -- the LogoutVital vital entry's fixed spans.
_VITAL_WRAPPER_TAG = 0x12
_VITAL_ID_LE = bytes.fromhex("401B")  # 0x1B40, little-endian
_VITAL_ENTRY_HEADER_TAIL = bytes.fromhex("0B00")
_SUBCODE_TAG = 0x08
_PAYLOAD_TAIL_12 = bytes.fromhex("080014000000001400000000")

_PREFIX_LEN = 13
_COUNT_BYTE_OFFSET = 13
_RESERVED_BYTE_OFFSET = 14
_VITAL_ENTRY_OFFSET = 15
_VITAL_ENTRY_LEN = 19
_MIN_FRAME_LEN = _VITAL_ENTRY_OFFSET + _VITAL_ENTRY_LEN  # 34


@dataclass(frozen=True)
class LogoutVitalRequestClassification:
    """Result of successfully classifying a LogoutVital request frame.

    ``trailing_bytes`` is returned verbatim and unparsed: this module makes
    no claim about what it contains (see module docstring). It is empty
    for the historical 34-byte one-vital-only capture shape and non-empty
    when the client's envelope bundled other vitals alongside LogoutVital
    (confirmed for subcode 1 in the 2026-09-01 capture).
    """

    subcode: int
    envelope_vital_count: int
    trailing_bytes: bytes

    @property
    def trailing_byte_count(self) -> int:
        return len(self.trailing_bytes)

    @property
    def is_exit_game(self) -> bool:
        return self.subcode == LOGOUT_SUBCODE_EXIT_GAME

    @property
    def is_character_select(self) -> bool:
        return self.subcode == LOGOUT_SUBCODE_CHARACTER_SELECT


def classify_logout_vital_request(
    frame: bytes,
) -> LogoutVitalRequestClassification | None:
    """Structurally classify a candidate LogoutVital request frame.

    Returns ``None`` (fail closed) for anything that does not match every
    fixed span exactly -- too short, wrong prefix, unrecognised subcode,
    or a payload tail that does not match the two captured pins' shape.
    Never raises on malformed input; never guesses a value it cannot
    verify from the frame itself.
    """

    if not isinstance(frame, (bytes, bytearray)):
        return None
    frame = bytes(frame)

    if len(frame) < _MIN_FRAME_LEN:
        return None
    if frame[0:_PREFIX_LEN] != _ENVELOPE_PREFIX_13:
        return None

    vital_count = frame[_COUNT_BYTE_OFFSET]
    if vital_count < 1:
        return None
    if frame[_RESERVED_BYTE_OFFSET] != _BYTE_14_RESERVED:
        return None

    entry = frame[_VITAL_ENTRY_OFFSET:_VITAL_ENTRY_OFFSET + _VITAL_ENTRY_LEN]
    if entry[0] != _VITAL_WRAPPER_TAG:
        return None
    if entry[1:3] != _VITAL_ID_LE:
        return None
    if entry[3:5] != _VITAL_ENTRY_HEADER_TAIL:
        return None
    if entry[5] != _SUBCODE_TAG:
        return None

    subcode = entry[6]
    if subcode not in LOGOUT_SUBCODES:
        return None
    if entry[7:19] != _PAYLOAD_TAIL_12:
        return None

    trailing = frame[_MIN_FRAME_LEN:]
    return LogoutVitalRequestClassification(
        subcode=subcode,
        envelope_vital_count=vital_count,
        trailing_bytes=trailing,
    )
