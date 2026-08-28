"""LANE-GM: read a GM command out of the ordinary chat box (0xAC52).

WHY THIS MODULE EXISTS
----------------------
The lane's original GM-002/GM-003 plan routed GM commands through the
client's own GM surface: the `BT_GM` button opens `GMUI_BASIC`, the player
types there, the client sends `GM_RunGMCommandVital` (0x51E9), and
`gm/dispatch.py` picks it up.  Two attended rounds have now measured that
that door does not open:

  * GT-101-R3 (2026-08-28 02:15 +07:00): the 41-byte GM_UpdateGMStateVital
    frame is accepted and `BT_GM` becomes visible -- but clicking it is
    silent.  No window, no error, no packet.
  * GT-103 steps 2a/2b (2026-08-28 11:36 +07:00): clicked in FOUR different
    UI states (empty HUD, map window held open, bag held open, bag closed
    again).  Silent in every one.  Inbound frame census for the whole boot:
    `0x51E9` = 0.  `TargetPosVital` x3 in the same window proves the client
    was alive and sending -- it is the button, not the session.

That result falsified RE-118's practical "give the dispatcher a non-empty
current-UI key first" hypothesis, and the remaining static question (which
control object `[0x0053B9B0]` is actually bound to) is RE-126's, not this
module's.  Meanwhile the lane's whole reason to exist -- be the tool that
gets a tester to a testable state -- was blocked behind a button.

This module takes the other door, the one RE-118's own follow-up list
called out as item (5), "is there a cheaper entry to GMUI_BASIC": there is,
and it does not involve GMUI_BASIC at all.  The client ALREADY sends every
line the player types in the ordinary chat box to the server, as
`Channel_LocalTalkMessageVital` (0xAC52), in a layout this project has
measured three separate times.  A GM types `/warp 2` in the same chat box
every player uses; the server reads it here.  No GM window, no `BT_GM`, no
0x51E9, no new client behavior to discover.

WIRE LAYOUT AND ITS PROVENANCE (two layers, per house rule)
-----------------------------------------------------------
Layer 1 -- wire capture, three samples of three different lengths:
  GT-006 (`reports/PF_GT006_CHAT_INPUT_UNKNOWN_FRAME_WIRE_CAPTURE_20260817.md`)
  and GT-009, tabulated in
  `pf_bridge/reports/PF_CHAT_ECHO002_SPEAKER_FIELD_RESEARCH_20260818.md`
  section (a).  Typing N ASCII characters and pressing Enter emits exactly
  one 0xAC52 payload of `10 + 2*N` bytes:

    | typed                | N  | payload | first 10 bytes                  |
    | `PFCHATPROBE1/2/9`   | 12 |     34B | `48 00 00 00 00 48 18 00 00 00` |
    | `SHORT`              |  5 |     20B | `48 00 00 00 00 48 0A 00 00 00` |
    | `PFCHATPROBETOOLONG` | 18 |     46B | `48 00 00 00 00 48 24 00 00 00` |

  0x18/0x0A/0x24 = 24/10/36 = 2*(12/5/18).  The length field varies with
  the text, in three samples, exactly as a byte length must.

Layer 2 -- the same serialization proven Grade A elsewhere in the client:
  `tag 0x48, u32 LE byte length, strict UTF-16LE, no terminator` is how
  `actor_wire.read_name()` reads the character name out of
  CreateActorDataEx and how StartGame's ActorAttr writes it
  (`reports/PF_CHARACTER_NAME001_PLAYER_NAME_PROJECTION_STATIC_IMPLEMENTATION_20260816.md`).
  So the reading here is not a chat-only guess: it is the client's standard
  wide-string encoding, met again.

Payload = wstring#1 (speaker, always empty client->server in every captured
sample) + wstring#2 (the typed text).  Total = 5 + n1 + 5 + n2.

WHAT IS NOT CLAIMED
-------------------
1. [no claim] that wstring#1 is the speaker-name field.  Every captured
   sample has it empty, so its MEANING is inferred (the CHAT-ECHO-002
   research grades it "ปานกลาง"); this module only requires it to be
   present and well-formed and never reads a value out of it.  Nothing here
   breaks if it turns out to be a channel id or an actor id instead.
2. [no claim] that a real client can send non-ASCII (Thai) text through
   this path, or how.  Every captured sample is ASCII.  The decoder below
   accepts any strictly-decodable UTF-16LE because that is what the
   encoding says, not because a Thai sample was ever measured.
3. [no claim] that any command reaching `parse_gm_command` here has a
   gameplay effect.  This module authorizes, decodes, parses and audits;
   execution is still `gm/warp_executor.py`'s and its callers' business,
   and `log_gm_command` still writes `executed: False`.
4. [no claim] about what a real client does.  The production path now
   reaches this module: CORE-REQUEST-GM-028 landed the second
   `lane_hooks.fire()` site in runtime.py, at the 0xAC52 branch, and
   `lane_hooks/lane_gm_chat_command.py` is registered on it -- proven
   headless on a flagless boot by
   `tests/test_gm_chat_command_dispatch_wiring.py`.  What is still unproven
   is the layer no test here can reach: that a GM typing into the real
   client's chat box produces the payload shape this module decodes.
   `GT-127` asks the bridge for exactly that.

SAFETY ORDER (deliberate, and the reason the checks are in this sequence)
------------------------------------------------------------------------
The GM-account check runs FIRST, before the payload is decoded at all.
That is not an optimization: the payload of a 0xAC52 frame is the literal
sentence a player typed to another player.  A player who is not a GM must
have their chat neither decoded, nor pattern-matched, nor written anywhere
by this lane -- this module refuses on identity alone and returns holding
no text.  A GM's own non-command chatter is decoded (it has to be, to see
there is no sigil) but is likewise never logged: only a line that starts
with the sigil AND parses becomes an audit record.

Default remains "nobody is a GM": `gm/accounts.py` reads an allowlist that
ships empty, the identity checked is the connection's authenticated login
name, and nothing in the payload can name the account it is checked
against.  A client cannot promote itself here any more than anywhere else
in this lane.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
import unicodedata

from . import accounts as gm_accounts
from .commands import (
    DEFAULT_LOG_PATH,
    GmCommand,
    GmCommandArgsError,
    GmCommandParseError,
    log_gm_command,
    parse_gm_command,
)
from .dispatch import (
    REFUSAL_LOOKUP_FAILED_PREFIX,
    REFUSAL_NOT_GM,
    REFUSAL_RATE_LIMITED,
    rate_limit_allows,
)

# Channel_LocalTalkMessageVital, named by the client's own registry
# (pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv line 259).
# Older code in this repo still calls it UNKNOWN_0xAC52 (its capture-era
# name from before that registry existed) -- same frame.
CHAT_LOCAL_TALK_VITAL_ID = 0xAC52

# tag 0x48 + u32 LE byte length, twice.  See module docstring for the two
# evidence layers behind these three constants.
WSTRING_TAG = 0x48
WSTRING_HEADER_LENGTH = 5
MIN_CHAT_PAYLOAD_LENGTH = 2 * WSTRING_HEADER_LENGTH

# The sigil that separates "a GM typing a command" from "a GM chatting".
# Chosen, not measured: the client has no `/xxx` command strings anywhere
# in it (the founding order's own finding), so the command vocabulary is
# ours to define and nothing in the client competes for this prefix.  A
# leading `/` is also what the owner's GM-002 test entry proposed trying
# first, and what every other game this project's testers have used means.
CHAT_COMMAND_SIGIL = "/"

# Bound before any allocation, same threat model as dispatch.py's
# MAX_RAW_PAYLOAD_LENGTH: a hostile or scripted client can put any length
# on the wire regardless of what the chat box's own input field allows, and
# this module must not turn that into a multi-megabyte decode.  A real chat
# line is tens of bytes; the largest command this lane defines is
# `say <=480 chars` (commands.MAX_SAY_MESSAGE_LENGTH), so 4 KiB leaves an
# order of magnitude of headroom over any legitimate line.
MAX_CHAT_PAYLOAD_LENGTH = 4096

# pf-adversary (round hs9m2r): `commands.log_gm_command` has exactly one
# live caller in this tree -- this module -- so this module is what makes
# its ndjson file reachable for the first time, and it inherited the gap
# `dispatch.py` had already closed on its own capture-file side
# (MAX_CAPTURED_BYTES_PER_ACCOUNT). The shared rate limiter is deliberately
# generous enough never to refuse a human (20 calls / 5 s), so a scripted
# GM account issuing `/say <478 chars>` at its legal sustained rate appends
# ~500-650 bytes per call, forever, to one flat append-only file -- hundreds
# of MB a day, inside the limiter's accepted operating range, with nothing
# to rotate or cap it. Same threat model, same answer: refuse once the file
# passes the cap rather than let a GM credential fill the disk.
#
# Checked against the file's real size on each command (one stat call, only
# on the already-rare authorized-command path), not against a counter kept
# in memory: the file survives process restarts and this lane's own
# .gitignore documents `capture/` as never cleaned up, so an in-process
# counter would reset to zero every boot and the cap would never bind.
MAX_COMMAND_LOG_BYTES = 64 * 1024 * 1024  # 64 MiB

# Unicode format characters (category Cf) -- bidi overrides U+202A..U+202E
# and isolates U+2066..U+2069 above all -- render a line of text in an
# order other than the one its bytes are in. `json.dumps` escapes the
# C0 control range, so an audit record cannot be split across ndjson lines
# (verified), but Cf characters are >= 0x20 and pass through verbatim.
# An audit log exists to say what a GM actually typed; a record that
# displays as something else in any terminal or viewer that honours bidi
# defeats that. Refused on COMMAND lines only -- ordinary chat is never
# decoded for a non-GM and never logged for a GM, so nothing here
# constrains what players may say to each other.
REFUSAL_PAYLOAD_TOO_LARGE = "chat_payload_too_large"
REFUSAL_UNDECODABLE_PREFIX = "chat_payload_undecodable_"
REFUSAL_NOT_A_COMMAND = "not_a_command"
REFUSAL_PARSE_ERROR_PREFIX = "command_parse_error_"
REFUSAL_LOG_WRITE_FAILED_PREFIX = "command_log_write_failed_"
REFUSAL_LOG_QUOTA_EXCEEDED = "command_log_quota_exceeded"
REFUSAL_UNSAFE_COMMAND_TEXT = "command_text_has_format_characters"


class ChatDecodeError(ValueError):
    """The bytes are not a well-formed 0xAC52 payload.

    Raised only by `decode_local_talk_payload`; `handle_local_talk_chat`
    catches it and turns it into a refusal reason rather than propagating,
    the same way `handle_gm_run_command_vital` never raises for a bad
    allowlist.  A frame the server cannot read must not take down the
    connection thread that read it.
    """


@dataclass(frozen=True)
class ChatCommandOutcome:
    """Result of one `handle_local_talk_chat` call.

    `authorized` False means the account is not a GM (or the allowlist
    could not be read) -- and in that case NOTHING was decoded: `text` and
    `command` are None because this module never looked at the bytes, not
    merely because it found nothing in them.  See the module docstring's
    safety-order section.

    `authorized` True with `command` None is every other refusal: the
    account really is a GM, but this particular line was oversized,
    undecodable, not a command (no sigil), rate limited, ungrammatical, or
    could not be written to the audit log.  `refusal_reason` says which.

    `text` is the decoded chat line, sigil included, and is set for a GM
    account from the decode step onward -- including on a parse refusal, so
    a caller can log what a GM mistyped.  It stays None for a non-GM
    account and for an undecodable payload.
    """

    authorized: bool
    command: GmCommand | None
    text: str | None
    refusal_reason: str | None


def decode_local_talk_payload(payload: bytes) -> tuple[str, str]:
    """Decode one 0xAC52 payload into `(speaker, message)`.

    `payload` is the nested vital's payload bytes only -- after the vital
    id and version in the runtime-vital envelope -- the same slice
    `gm/command_capture.py` and `gm/dispatch.py` already expect.  This
    function does not strip an envelope.

    Fails closed on every deviation from the measured shape rather than
    salvaging what it can: a frame this lane cannot read exactly is a frame
    it must not act on.  In particular an odd byte length, a length field
    that does not account for every remaining byte, a wrong tag, or bytes
    that are not strictly decodable UTF-16LE all raise -- no lenient
    `errors="replace"` anywhere, because a replacement character inside a
    command argument would be an invented value.
    """
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    raw = bytes(payload)
    if len(raw) < MIN_CHAT_PAYLOAD_LENGTH:
        raise ChatDecodeError(
            f"payload shorter than two wstring headers: {len(raw)}"
        )

    fields: list[str] = []
    offset = 0
    for index in (1, 2):
        if offset + WSTRING_HEADER_LENGTH > len(raw):
            raise ChatDecodeError(f"truncated before wstring#{index} header")
        if raw[offset] != WSTRING_TAG:
            raise ChatDecodeError(
                f"wstring#{index} tag is 0x{raw[offset]:02X}, "
                f"expected 0x{WSTRING_TAG:02X}"
            )
        (byte_length,) = struct.unpack_from("<I", raw, offset + 1)
        offset += WSTRING_HEADER_LENGTH
        # Checked before the slice, not after: a length field of 0xFFFFFFFF
        # must be a refusal, never a silently-short Python slice that then
        # decodes to whatever happened to be there.
        if byte_length > len(raw) - offset:
            raise ChatDecodeError(
                f"wstring#{index} length {byte_length} exceeds "
                f"{len(raw) - offset} remaining bytes"
            )
        if byte_length % 2:
            raise ChatDecodeError(
                f"wstring#{index} length {byte_length} is not a whole "
                "number of UTF-16 code units"
            )
        try:
            fields.append(
                raw[offset:offset + byte_length].decode("utf-16-le")
            )
        except UnicodeDecodeError as error:
            raise ChatDecodeError(
                f"wstring#{index} is not strict UTF-16LE: {error.reason}"
            ) from error
        offset += byte_length

    if offset != len(raw):
        # Every captured sample accounts for all of its bytes
        # (5 + n1 + 5 + n2 == payload length, three samples, three lengths).
        # Trailing bytes mean this is not the frame shape measured, so this
        # module does not know what it is holding.
        raise ChatDecodeError(
            f"{len(raw) - offset} trailing bytes after wstring#2"
        )
    speaker, message = fields
    return speaker, message


def _command_log_quota_allows(log_path: Path) -> bool:
    """False once the audit log has grown past `MAX_COMMAND_LOG_BYTES`.

    A missing file is allowed (nothing written yet).  An `OSError` while
    stat-ing is ALSO allowed through, deliberately: this guard exists to
    bound disk growth, and turning "cannot stat the log" into a refusal
    would let an unreadable directory silently disable every GM command,
    which is a worse failure than one more appended line.  The write
    itself still fails closed a few lines later if the file is genuinely
    unwritable.
    """
    try:
        return log_path.stat().st_size < MAX_COMMAND_LOG_BYTES
    except FileNotFoundError:
        return True
    except OSError:
        return True


def has_format_characters(text: str) -> bool:
    """True if `text` contains a Unicode format (Cf) character.

    See `REFUSAL_UNSAFE_COMMAND_TEXT` for why this matters and why it is
    applied to command lines only.  Category test rather than a blacklist
    of specific code points: the bidi overrides and isolates are the ones
    with a known attack, but every Cf character is by definition invisible
    or reordering, and a GM command has no legitimate use for any of them.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    return any(unicodedata.category(character) == "Cf" for character in text)


def looks_like_gm_command(text: str) -> bool:
    """True if `text` is a line a GM meant as a command, not as chat.

    Deliberately narrow: the sigil must be the very first character, with
    no leading whitespace tolerated.  A player (GM or not) who begins a
    sentence with a space then a slash is chatting, and a lane that guessed
    otherwise would silently eat a chat line.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    return text.startswith(CHAT_COMMAND_SIGIL)


def handle_local_talk_chat(
    account_name: str,
    payload: bytes,
    *,
    config_path: str | None = None,
    log_path: str | None = None,
    now_ts: float | None = None,
) -> ChatCommandOutcome:
    """Authorize, decode, parse and audit one inbound 0xAC52 chat line.

    `account_name` must be the authenticated login name for the connection
    this payload arrived on -- `runtime.py`'s `self.token`, the same value
    `handle_gm_run_command_vital` requires and for the same reason: the
    client has no message that grants or claims GM status for itself, so
    the identity checked here must never be read out of `payload`.

    Applies no gameplay effect.  A caller that wants one takes
    `outcome.command` and routes it (today: `gm/warp_executor.py` for
    `warp`, `gm/say_wire.py` for `say`); this function's contract ends at
    "a GM really typed this, it parses, and it is now in the audit log".
    """
    # `type(...) is not str`, not isinstance: this value flows into the
    # allowlist test, where a str subclass lying through __eq__/__hash__ is
    # the exact bypass accounts.is_gm_account closes.  Same check, same
    # reasoning, one call earlier -- identical to dispatch.py's entry point.
    if type(account_name) is not str or not account_name:
        raise ValueError("account_name must be a non-empty str")
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    # pf-adversary (round hs9m2r): snapshot ONCE, here, before the size
    # check reads a length that the decode step would otherwise re-read
    # from the same object. Every caller today hands over an immutable
    # `bytes` (runtime.py's 0x51E9 site passes `bytes(parsed.nested_payload)`
    # and the chat site is specified the same way), so this is not a live
    # race -- but nothing in this signature stops a future caller from
    # passing a shared `bytearray` another thread mutates between the two
    # reads, which is the check-then-use class this module refuses to be
    # sloppy about anywhere else.
    payload = bytes(payload)

    # IDENTITY FIRST.  Everything below this block touches the sentence a
    # human typed; a non-GM's chat must not reach any of it.
    try:
        is_gm = gm_accounts.is_gm_account(account_name, config_path)
    except (ValueError, OSError) as error:
        return ChatCommandOutcome(
            authorized=False,
            command=None,
            text=None,
            refusal_reason=(
                f"{REFUSAL_LOOKUP_FAILED_PREFIX}{type(error).__name__}"
            ),
        )
    if not is_gm:
        return ChatCommandOutcome(
            authorized=False,
            command=None,
            text=None,
            refusal_reason=REFUSAL_NOT_GM,
        )

    if len(payload) > MAX_CHAT_PAYLOAD_LENGTH:
        return ChatCommandOutcome(
            authorized=True,
            command=None,
            text=None,
            refusal_reason=REFUSAL_PAYLOAD_TOO_LARGE,
        )

    try:
        _speaker, text = decode_local_talk_payload(payload)
    except ChatDecodeError as error:
        return ChatCommandOutcome(
            authorized=True,
            command=None,
            text=None,
            refusal_reason=(
                f"{REFUSAL_UNDECODABLE_PREFIX}{type(error).__name__}"
            ),
        )

    if not looks_like_gm_command(text):
        # A GM chatting normally.  Not an error, not logged, not counted
        # against the rate limit -- this lane is invisible on this line.
        return ChatCommandOutcome(
            authorized=True,
            command=None,
            text=text,
            refusal_reason=REFUSAL_NOT_A_COMMAND,
        )

    if has_format_characters(text):
        return ChatCommandOutcome(
            authorized=True,
            command=None,
            text=text,
            refusal_reason=REFUSAL_UNSAFE_COMMAND_TEXT,
        )

    # Rate limit AFTER the sigil check, so a GM's ordinary conversation
    # never consumes the budget a real command needs.  The window is shared
    # with the 0x51E9 path on purpose (see dispatch.rate_limit_allows): the
    # thing being bounded is GM actions per account, not frames per door.
    #
    # pf-adversary (round hs9m2r) is right that "one shared budget" is
    # therefore not literally true in both directions: the 0x51E9 path
    # spends a slot before checking payload size, this path checks size
    # first, so an oversized chat frame is discarded without touching the
    # window. Recorded rather than "fixed" by reordering, because both
    # orderings are O(1) rejections and the alternative -- moving the
    # limiter ahead of the sigil check -- would charge a GM's ordinary
    # conversation against the budget their next real command needs, which
    # is the property this ordering exists to protect. The invariant that
    # actually matters (a GM cannot exceed the per-account ceiling by
    # splitting real commands across the two doors) holds either way.
    if not rate_limit_allows(account_name, now_ts):
        return ChatCommandOutcome(
            authorized=True,
            command=None,
            text=text,
            refusal_reason=REFUSAL_RATE_LIMITED,
        )

    try:
        command = parse_chat_command_text(text)
    except (GmCommandParseError, GmCommandArgsError) as error:
        return ChatCommandOutcome(
            authorized=True,
            command=None,
            text=text,
            refusal_reason=(
                f"{REFUSAL_PARSE_ERROR_PREFIX}{type(error).__name__}"
            ),
        )

    resolved_log_path = Path(
        log_path if log_path is not None else DEFAULT_LOG_PATH
    )
    if not _command_log_quota_allows(resolved_log_path):
        return ChatCommandOutcome(
            authorized=True,
            command=None,
            text=text,
            refusal_reason=REFUSAL_LOG_QUOTA_EXCEEDED,
        )

    # Fail closed on an unwritable audit log: this lane's whole permission
    # story is "a named GM account did a named thing at a named time", and
    # a command the server cannot record is a command it should not hand
    # onward.  Returning the command anyway would let a full or read-only
    # disk silently turn audited GM actions into unaudited ones.
    try:
        if log_path is None:
            log_gm_command(command, account_name, now_ts=now_ts)
        else:
            log_gm_command(
                command, account_name, log_path=log_path, now_ts=now_ts
            )
    except OSError as error:
        return ChatCommandOutcome(
            authorized=True,
            command=None,
            text=text,
            refusal_reason=(
                f"{REFUSAL_LOG_WRITE_FAILED_PREFIX}{type(error).__name__}"
            ),
        )

    return ChatCommandOutcome(
        authorized=True, command=command, text=text, refusal_reason=None,
    )


def parse_chat_command_text(text: str) -> GmCommand:
    """Strip the sigil and hand the rest to the lane's own grammar.

    Kept separate from `handle_local_talk_chat` so the sigil convention has
    exactly one definition and a test can drive the grammar without
    building a wire payload.  `GmCommand.raw` therefore carries the command
    WITHOUT the sigil, matching what a 0x51E9-sourced command would carry
    for the same typed words -- the audit log must not record the same
    action two different ways depending on which door it came through.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    if not looks_like_gm_command(text):
        raise GmCommandParseError("text does not start with the command sigil")
    return parse_gm_command(text[len(CHAT_COMMAND_SIGIL):])
