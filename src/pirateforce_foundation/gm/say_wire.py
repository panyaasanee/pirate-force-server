"""Bridges a parsed GM-003 `say` command into a real outbound
`Channel_GMGlobalMessageVital` (0x9F2C) wire frame.

`gm/commands.py` parses `say <message...>` into a `GmCommand` but does not
build a wire frame for it -- its own docstring says wiring `say` needs the
0x9F2C `Channel_GMGlobalMessageVital` codec, and left that unbuilt. The
retracted broadcast-wire round (`rounds/GM_20260827_1415_broadcast-wire-
attempted-and-retracted.md`) found the reason this lane must NOT build a
second, competing wire codec for that vital: `channel_message_hypothesis.py`
(CHAT-CHANNEL-001/002, committed 2026-08-18, byte-exact static read of the
client binary plus a three-way hash cross-check against a real captured
frame) already owns the proven encoder for `Channel_GMGlobalMessageVital`
and the four sibling channels that share serializer `0x65AD40` -- the
`gm/broadcast_wire.py` this lane wrote and deleted in that round assumed an
untagged wstring pair straight off `PF_SERIALIZER_FIELDS.tsv`'s coarser tag
column; the real wire carries a `0x48` tag + u32 byte-length header per
string that only `channel_message_hypothesis.py` had already proven.

This module therefore imports that encoder rather than re-deriving it
(GM-003's own rule, notes_to_chief 20260826_1630: reuse another lane's
proven work via import, never by copying its logic into this lane's zone).
It adds no new wire knowledge -- it only adapts a parsed `GmCommand` to the
existing `encode_channel_message`/`make_channel_message_response` call
shape, the same role `gm/warp_executor.py` plays for `gm/teleport_wire.py`.

This module does not read off a live socket, does not track player state,
and does not send anything -- it returns frame bytes for a caller to send,
same posture as `gm/warp_executor.py`. Wiring a real send is CORE-REQUEST
territory (see docs/GM_LANE.md).

`pf-adversary` (say-wire round) found two gaps against the "regardless of
source" contract this module's docstring already claimed:

1. `gm/commands.py`'s `MAX_SAY_MESSAGE_LENGTH` cap is enforced only inside
   `parse_gm_command`, by that module's own comment specifically so a
   "fat-fingered or hostile `say`" cannot grow unbounded "once execution is
   wired in" -- this module IS that execution wiring, and a hand-built
   `GmCommand` bypasses `parse_gm_command` entirely, so the cap must be
   re-checked here too, not merely inherited by convention.
2. `command.args` was indexed/measured with plain `len()`/`[0]`, which
   raises a bare `TypeError`/`KeyError`/`IndexError` (never `SayWireError`)
   for an `args` container of the wrong *shape* (not `None`, not missing
   `__len__`, not a mapping) -- the checked-in tests only ever varied
   `args`' *values*, never its *shape*, so this gap shipped asserted-safe
   without being exercised.

The warp-executor args-shape follow-up round then fixed the identical gap
in `gm/warp_executor.py` and found the `say_wire.py`-style three-type catch
itself (`TypeError`/`KeyError`/`IndexError`) still left two gaps open,
flagged in `docs/GM_LANE.md` as this module's own follow-up: (a) a custom
`__len__`/`__getitem__` raising anything outside those three types (e.g.
`AttributeError`, `ValueError`) would still leak past this module's own
"every failure surfaces as `SayWireError`" promise; (b) a `str`/`bytes`
scalar of length 1 (e.g. `"x"`) passes `len(args) == 1` and is positionally
indexable, so it would be read as a real one-element args sequence instead
of being refused as the wrong container shape.

A later round (`say-wire args-shape follow-up`, not the warp-executor round
itself) first applied that same blacklist-style fix here (broad `except
Exception` plus an `isinstance(args, (str, bytes))` reject), then
`pf-adversary` broke it again the same day: an integer-keyed `dict` (e.g.
`{0: "hello"}`) is exactly the "mapping" shape `docs/GM_LANE.md` already
names as one of the three canonical wrong shapes (`None`, a `set`, a
`dict`), yet `len(d)` and `d[0]` both succeed normally for it -- no
exception is ever raised, so neither the `str`/`bytes` guard nor either
`except Exception` clause fires, and a hand-built `GmCommand` with such a
dict silently builds a real frame. `warp_executor.py` has the identical
gap for the same reason. Enumerating one more forbidden shape every time
adversary finds one that happens not to raise is an unbounded blacklist
against a `tuple[str, ...]`-typed field (see `gm/commands.py`'s
`GmCommand.args` annotation) with exactly one legitimate shape -- so this
module now asserts that shape directly (`isinstance(args, tuple)`) instead
of continuing to chase individual non-tuple shapes that happen not to
raise. Every non-`tuple` `args` -- `None`, a `set`, a `dict` of any key
type, a `str`/`bytes` scalar, a `bytearray`, a custom object, a `list` --
is refused up front, before `len()`/indexing ever runs.
"""
from __future__ import annotations

from ..channel_message_hypothesis import (
    SHARED_SERIALIZER_CHANNEL_IDS,
    make_channel_message_response,
)
from .commands import MAX_SAY_MESSAGE_LENGTH, GmCommand

GM_GLOBAL_CHANNEL_ID = SHARED_SERIALIZER_CHANNEL_IDS["Channel_GMGlobalMessageVital"]

# The OTHER channel this module composes for, and it is a different question
# from the gated one above in every way that matters.
#
# COO-DECISION 2026-09-02T03:45+07:00 (`pf_bridge/notes_to_chief/20260902_
# 0345_COO-DECISION-speed-refusal-localtalk-via-say-wire-12-ascii.md`) ordered
# path 1 for GM-B's "a refused /speed must say so ON SCREEN": compose the
# notice on `Channel_LocalTalkMessageVital` (0xAC52), from THIS file, because
# `tests/test_gm_say_gate_lock.py::NoSecondCompositionRouteTests` makes this
# the only module in the lane's zone allowed to reach the shared codec at all.
#
# WHAT IS DIFFERENT ABOUT 0xAC52, AND WHAT IS NOT -- CORRECTED after
# pf-adversary (round `aa9ajr`, D5) refuted the first draft of this block from
# this repository's own files.  The struck sentence read: ~~"this server
# already puts 0xAC52 frames composed by this very codec onto real sockets on
# the production path, so the render is measured at the client-observable
# rung"~~.  It is not: the echo lane that GT-009 measured runs behind a
# scenario opt-in whose own file says `"production_allowed": false`, it echoes
# the CLIENT's own frame rather than server-composed text, and a chat-keyed
# scenario boot and the GM branch are mutually exclusive.
#
# EXPIRED 2026-09-02 BY `GT-205`, STRUCK RATHER THAN DELETED.  Both sentences
# below were true when this block was written and are not any more:
# ~~"NO SERVER-COMPOSED 0xAC52 LINE HAS EVER BEEN SEEN ON A SCREEN ON A
# DEFAULT BOOT."~~ and ~~"`GT-193` step 9 is the first attempt."~~  Attended
# round R303 ran `GT-205` with the owner at the keyboard and the chat line
# `[thua pai] : BACK REFUSED` -- composed by THIS module's
# `make_local_talk_notice_frame`, through `world_logout_button_notice` --
# appeared on her screen.  (LANE-A letter `20260903_1131`, handed to this
# lane by chief `20260903_1304` point 3; `gm/` is this lane's zone, so the
# correction is made here rather than by them.)
#
# WHAT R303 THEREFORE DOES *NOT* LICENSE.  Four limits, and nothing wider may
# be read out of the strike above:
#   1. IT DID NOT MEASURE THE WIRE/DB RUNG.  The result letter says so in its
#      own words -- "not separately instrumented for this ticket" -- so the
#      screen is the only rung R303 grades.
#   2. IT DID NOT RECORD whether the logout dialog was still open when the
#      line appeared.
#   3. THE LENGTH STAYS PINNED AT 12 CHARACTERS.  R303 saw a 12-character
#      body render; it did not license 5 or 26, and the constant below is
#      still chosen by GT-006/GT-009 rather than by that round.
#   4. "DEFAULT BOOT" IS STILL NOT ESTABLISHED, and this limit is the one
#      chief did not list -- it comes from LANE-A's own module on `main`
#      (`world_logout_button_notice.py:76-90`), which measured that the
#      result letter records no argv, so the boot is known to have carried NO
#      LOGOUT SCENARIO but is NOT known to have been flagless.  The struck
#      sentence is retired because a server-composed line of this channel HAS
#      now rendered, not because anybody proved the boot was default.
# !! THIS IS A COMMENT CORRECTION AND UNLOCKS NOTHING.  `GT-193` steps 4-7
# remain ungradeable (chief `0815`, COO `0845`), and no gate in this file
# moved with it.
#
# What IS true, and is what the composer below rests on:
#   * the PAYLOAD codec for this channel is byte-pinned against real captured
#     frames (CHAT-ECHO-001/002), which 0x9F2C's never was;
#   * GT-009 measured a 12-printable-ASCII body RENDERING in the client's chat
#     window, and a 5-character one staying silent -- which is why the length
#     below is pinned rather than chosen; and
#   * neither reason the GMGlobal gate is shut applies to this route: it does
#     not broadcast (the frame answers the one connection whose command is
#     being refused, so "who may speak to the whole server" is not asked), and
#     the render question above is exactly what `GT-193` step 9 decides.
# This constant is NOT a second gate and must never be read as one: it is a
# channel id, and the locked gate below is untouched by this block.
LOCAL_TALK_CHANNEL_ID = SHARED_SERIALIZER_CHANNEL_IDS[
    "Channel_LocalTalkMessageVital"
]

# The 12 ASCII characters, exactly, and the length is evidence, not taste.
# COO-DECISION `0345` item 2, translated (source files stay ASCII, the bridge
# console is cp874): "the attended evidence exists at length 12 only -- a
# 5-character body was silent, a 26-character one nobody measured".
# In this lane's own words: the only body length anybody has watched
# render on this channel is 12 (`PFCHATPROBE1`/`PFCHATPROBE2`, GT-006/GT-009);
# a 5-character body was measured SILENT and a 26-character one has never been
# measured at all.  Every refusal path uses this one string so that a tester
# never has to tell two on-screen sentences apart, and so that the round that
# widens it has to move a pinned length rather than a habit.
SPEED_DENIED_NOTICE_TEXT = "SPEED DENIED"

# THE SECOND SENTENCE, AND IT IS A SECOND ONE BECAUSE THE FIRST WOULD LIE.
# COO-DECISION 2026-09-02T06:47+07:00 (`pf_bridge/notes_to_chief/consumed/
# 20260902_0647_COO-DECISION-typo-layer-notice-is-TYPO-REFUSED-12-ascii-after-
# p1.md`), item 1: the SYNTAX layer -- `parse_gm_command`'s refusal, which
# `gm/chat_command.py` reports as `command_parse_error_*` -- gets its own
# body, `TYPO REFUSED`, for every command name and not just `/speed`.
#
# Why not reuse the string above: `SPEED DENIED` in answer to a mistyped
# `/warp` would name a command the GM did not type and a subsystem that never
# ran.  Why not a longer, clearer sentence: the length is the SAME pinned
# evidence the constant above rests on -- 12 printable ASCII characters is the
# only body length anybody has watched render on this channel -- so a second
# string had to be found INSIDE that length rather than written freely.  That
# is `0345` item 2's rule applied a second time, not a new rule.
#
# WHAT THE TWO SENTENCES BUY TOGETHER, and it is the whole point of splitting
# them: COO-DECISION `0147` asks a tester to tell "typo", "the DB refused it"
# and "the frame went out" apart FROM THE SCREEN.  With both strings shipped
# the screen answers the first two by wording and the third by silence.
TYPO_REFUSED_NOTICE_TEXT = "TYPO REFUSED"

NOTICE_TEXT_EXACT_LENGTH = 12

# Every captured GT-006 frame on this shared serializer has carried an empty
# speaker (channel_message_hypothesis.py docstring); this module does not
# invent a GM display name, so a caller who wants one must pass it.
DEFAULT_SPEAKER = ""

# The vital_version byte that `channel_message_hypothesis.
# make_channel_message_response` hardcodes for EVERY channel on serializer
# 0x65AD40 -- it is the middle element of the one tuple it hands
# `legacy.make_runtime_vitals`, and v141 writes it as `u8tag(0x0B, ...)` per
# nested vital (`current/pf_login_game_server_v141.py:702-704`, re-derived at
# this commit).  Named here, not because this lane may change it (that module
# is another lane's proven work and is NOT in this lane's write zone), but
# because the gate below has to be able to say WHICH byte it is gating.
CHANNEL_CODEC_VITAL_VERSION = 0

# !! THIS LANE'S SEND GATE FOR 0x9F2C.  `None` means: no vital_version byte
# has been proven for THIS vital, so no GM COMMAND may put a `say` frame on a
# real socket.
#
# THAT IS A LANE-LOCAL PROPERTY, NOT A REPO-WIDE ONE, and the first draft of
# this comment overstated it (pf-adversary, this round, enumerated every
# caller rather than trusting the sentence).  `make_channel_message_response`
# has exactly two call sites in `src/`: this module, and
# `runtime.py:2126-2147`, which is NOT gated by this constant.  Booted with
# `--channel-message-hypothesis-scenario .../channel_sweep.json`, that path
# already composes a real `Channel_GMGlobalMessageVital` frame carrying the
# very byte RE-132 is being asked to prove, and the v141 serve loop sends it
# (`v141:7755`).  So the honest claim is: no GM command can send one, and
# nothing in this lane can open that.
#
# WHICH MEANS RE-132 IS NOT THE ONLY INSTRUMENT AIMED AT THIS BYTE.
# `docs/HYPOTHESIS_LEDGER.json` and `docs/FUNCTIONAL_COVERAGE.json` both name
# **GT-016** as the queued attended test that sends all five shared-serializer
# channels, GMGlobal included, to a real client and reads what renders -- a
# client-observable measurement, which is a STRONGER layer than RE-132's
# static constructor read.  If GT-016 runs first and the client accepts the
# frame, that answers this byte from the higher rung and RE-132 becomes a
# corroboration rather than the gate's key.  Whoever opens this constant
# should check GT-016's state first.
#
# It is deliberately shaped like
# `teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED` and read at the same
# place -- the module that returns an ACTION, not this one, which stays a
# pure byte builder its own tests can exercise.
#
# WHAT IS PROVEN, AND IT IS A LOT (do not re-derive):
#   CHAT-CHANNEL-001 (`reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_
#   STATIC_20260818.md`, byte-exact static read) pins this channel's 16-bit
#   wire id 0x9F2C, pins that five channels share serializer 0x65AD40
#   wire-IDENTICALLY, and pins the field order and the `0x48` + u32-length
#   UTF-16LE wstring codec.  `channel_message_hypothesis.py` then reproduces
#   real captured GT-006 payload bytes and the CHAT-ECHO-001/002 pinned PC and
#   frame hashes exactly.  None of that is in question here.
#
# WHAT IS NOT PROVEN, AND IT IS EXACTLY ONE BYTE:
#   every one of those three byte-level cross-checks composes `channel_id ==
#   0xAC52` (Channel_LocalTalkMessageVital).  They pin the PAYLOAD codec,
#   which the family shares; they say nothing about the vital_version this
#   family's OTHER class ids are accepted with, because that byte is not part
#   of the payload -- it sits in the envelope, one per nested vital.
#   This lane has measured that byte four times and it is per-vital with no
#   project default: 0x5A19 -> 0 and ForcePos -> 0 and TeleportVital -> 4
#   (RE-105 / RE-129, from the client's own constructors), SelectActor -> 10
#   (server source, a different layer).  Inheriting 0xAC52's byte for 0x9F2C
#   because the payload codec is shared is precisely the reasoning shape that
#   produced the hardcoded `1` GT-101 measured as fatal on a real client
#   (modal `ErrorData=23065`, connection halted, socket closed).
#   `RE-132` (filed this round, via chief) asks for this vital's constructor
#   byte using the recipe RE-105/RE-129 already ran twice.
#
# !! WHO GETS TO OPEN THIS, AND IT IS NOT THIS LANE ALONE.
#   `teleport_wire`'s constant has an external lock (COO-DECISION
#   20260828_2130 + `tests/test_gm_force_pos_version_lock.py`).  This one had
#   nothing but the lane's own test -- and the release-day note below tells a
#   future round to edit that very test, so "who else has to agree" answered
#   itself with "nobody".  pf-adversary asked the question; the lane's answer,
#   pending COO ([สมมติของสาย GM - รอ COO ยืนยัน], letter filed round
#   `w8hnu9`), is that TWO conditions outside this lane must hold first:
#     (A) the per-connection identity question in `runtime.py`'s own
#         `IDENTITY, STATED HONESTLY` comment (lines 4886-4896 at this
#         commit; cite the ANCHOR, the line numbers drift) is
#         resolved -- while every connection shares one `--token`, opening
#         this gate hands `/say` to whoever connects, and the allowlist that
#         is supposed to stop them cannot tell two humans apart; and
#     (B) something has established that the client's GMGlobal branch RENDERS
#         a received frame (GT-016, or RE-132 question 3).  A byte-perfect
#         frame into a branch that draws nothing looks exactly like a wrong
#         version byte from the tester's chair.
#
# RE-132 CAME BACK, AND IT MOVED TWO OF THE FOUR ITEMS BELOW.  Result letter
# `notes_to_chief/20260829_0010_RE-132-RESULT-VERSION-ZERO-RENDER-PATH.md`
# (DONE/PASS, static, verifier 61/61), consumed by this lane in round
# `z6gu2n`.  What it settled, and the pins are in
# `GM_GLOBAL_MESSAGE_VITAL_VERSION_RE132_STATIC` below:
#   * step 1 -- the byte is 0, from the client's own base constructor
#     (`xor eax,eax` at 0x00657CB8, `mov byte ptr [esi+0x10],al` at
#     0x00657CC9), reached through the 0x9F2C prototype's ctor call at
#     0x0065BCD0.  It equals CHANNEL_CODEC_VITAL_VERSION, so branch 3 of the
#     ladder is dead and the codec needs no version parameter.
#   * (B), AT THE STATIC LAYER ONLY -- RE-132's question 3 found the handler
#     both vtables bind (0x0065C850) is not a no-op: it routes to 0x00659870,
#     the GMGlobal discriminator matches, the body wstring is read at
#     object+0x18 and a display sink is called at 0x0065A053.  That is a
#     client-binary fact, one rung BELOW client-observable, and the RE letter
#     says so itself in its nonclaims.
#     !! (B) IS NOT SATISFIED BY IT, and the first draft of this block said it
#     was "satisfied for the byte", which pf-adversary correctly called a
#     re-scope: (B) as written above is about the branch RENDERING, and the
#     byte was step 1's question, not (B)'s.  What RE-132 did is REMOVE THE
#     CHEAPEST WAY (B) COULD FAIL -- a handler that draws nothing, the
#     `mov al,1; ret 4` shape RE-129 found on ForcePos.  (B) still needs
#     GT-016 or GT-133: nobody has seen a line render.
# WHAT IT DID NOT MOVE, AND IT IS THE ONE THAT MATTERS: (A).  The identity
# question in `runtime.py`'s `IDENTITY, STATED HONESTLY` comment is
# untouched by anything static, and the
# RE letter closes with the same sentence -- the result "does not authorize
# the RE runner to open the gate".  So this constant stays None.
#
# WHAT IS ACTUALLY LEFT, COUNTED HONESTLY (the first draft said "exactly ONE
# item" and pf-adversary counted three):
#   (A) the identity fix -- nothing static can touch it;
#   COO's word on the flip -- item 0 has always been two conditions; and
#   (B) the SCREEN, from GT-016 or GT-133, at the client-observable rung.
# What is no longer left is the byte.  A round that flips this constant
# without (A) fixed is handing `/say` to every connection that shares the
# process `--token`, which is every connection.
#
# RELEASE DAY, IN ORDER:
#   0. (A) holds, and COO has said the flip is allowed, and (B) has been
#      answered at the client-observable rung.  [<- the remaining THREE]
#   1. RE-132 answers with a byte V for Channel_GMGlobalMessageVital.  [DONE:
#      V = 0]
#   2. If V == CHANNEL_CODEC_VITAL_VERSION, set this constant to V.  The
#      codec already emits that byte, so nothing else changes.  [V == 0 ==
#      CHANNEL_CODEC_VITAL_VERSION, so this step is a one-line edit whenever
#      step 0 clears.]
#   3. If V != CHANNEL_CODEC_VITAL_VERSION, STOP: setting this constant would
#      open a gate onto a frame the codec cannot build.  The version-mismatch
#      refusal in `gm/chat_command_action.py` catches that, but the fix is a
#      letter to `channel_message_hypothesis.py`'s owning lane asking for a
#      version parameter -- NOT a second codec in this lane's zone (that is
#      the round `rounds/GM_20260827_1415_broadcast-wire-attempted-and-
#      retracted.md` already tried and retracted).
#   4. Either way, release day edits THREE files, and ~~ONE test~~ is no
#      longer true.  The struck sentence read: "release day also edits ONE
#      test ... there is no second assertion on this one, because this lane
#      owns `say_wire.py`'s suite outright and did not need a separate lock
#      file for it."  COO-DECISION 2026-08-29T00:41+07:00 (`notes_to_chief/
#      20260829_0041_COO-DECISION-say-gate-lock-is-official-and-gt016-goes-
#      first.md`) is precisely the thing that made it false, and for the
#      reason the sentence itself gave away: a lane that owns the suite
#      outright can lift the lock in the same commit that wants the byte,
#      and COO ruled that is not a lock.  So release day now edits:
#        1. this file (the constant);
#        2. `tests/test_gm_say_action.py`'s `SayVersionGateTests` -- TWO
#           unconditional `assertIsNone`s, not one (`test_the_shipped_
#           constant_is_still_none_so_no_bytes_can_go_out` and `test_re132_is_
#           answered_and_the_gate_is_still_shut_for_the_other_reason`); and
#        3. `tests/test_gm_say_gate_lock.py` -- the separate lock file COO
#           ordered, which also refuses an UNGATED composer and a second
#           composition route through the shared codec.  Flipping the
#           constant alone leaves that file red, on purpose.
#      Same shape as ForcePos after all.  And the flip is not this lane's to
#      make: only a NEW COO-DECISION lifts it.
GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED: int | None = None

# The byte RE-132 measured, kept SEPARATE from the gate above on purpose.
#
# Two different questions were being answered by one constant, and holding
# them apart is what keeps the ledger honest in both directions:
#   * "what byte does the client's 0x9F2C constructor write?" -- answered, 0,
#     statically, and worth pinning so no later round re-opens an RE ticket
#     that has already been paid for; and
#   * "may this server put those bytes on a socket?" -- NOT answered, because
#     that one is about identity (A), not about bytes at all.
# Collapsing them would make the gate look like it is waiting for RE work
# that is finished, which is how a blocked lane gets re-measured instead of
# unblocked.  This constant is therefore read by tests and by readers; it is
# NEVER read by `chat_command_action._say_action`, which reads the gate.
GM_GLOBAL_MESSAGE_VITAL_VERSION_RE132_STATIC = 0
# Pins for the result this lane consumed, so a future round can tell whether
# it is looking at the same measurement (`GameClient.local.bin` SHA-256, plus
# the three VAs the answer hangs on: where the byte is written, the ctor call
# that proves it is 0x9F2C's, and the handler question 3 read).
RE132_CLIENT_IMAGE_SHA256 = (
    "9627211412ac60d50ad189ce5a629443ce928ec23a9f8d219dfb2b157028b623"
)
RE132_VERSION_WRITE_VA = 0x00657CC9
RE132_GM_GLOBAL_CTOR_CALL_VA = 0x0065BCD0
RE132_HANDLER_VA = 0x0065C850


class SayWireError(ValueError):
    """A `say` command cannot be composed into a `Channel_GMGlobalMessageVital`
    frame as given."""


class NoticeWireError(ValueError):
    """A one-line notice cannot be composed into a
    `Channel_LocalTalkMessageVital` frame as given.

    A type of its own, not a `SayWireError`: a caller that wants to keep
    running when a notice cannot be built must not accidentally swallow a
    `say` failure with the same clause, and the two failures mean different
    things to a reader of the event log.
    """


def make_local_talk_notice_frame(
    legacy, text: str, *, speaker: str = DEFAULT_SPEAKER,
) -> tuple[bytes, bytes]:
    """Build a server->client `Channel_LocalTalkMessageVital` frame carrying
    one short notice line, for the connection that is being answered.

    THIS IS NOT A `say`.  It composes 0xAC52 (the channel the client itself
    talks on, whose codec CHAT-ECHO-001/002 pinned against real captured
    bytes and whose render GT-009 measured), never 0x9F2C, and it reads
    nothing from `GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED` because that
    gate is about the OTHER channel.  It composes bytes and returns them;
    the caller decides whether they go anywhere, same posture as
    `make_say_broadcast_frame` and `gm/warp_executor.py`.

    `text` must be exactly `NOTICE_TEXT_EXACT_LENGTH` ASCII characters --
    see that constant's comment for why the length is a pinned property and
    not a style rule.  Every failure surfaces as `NoticeWireError`, never a
    bare `ValueError`/`RuntimeError` out of the codec.
    """
    if type(text) is not str:
        # Exact type, not `isinstance`: a `str` subclass can lie through
        # `__len__`/`__eq__`, which is the shape this module's own args check
        # was twice defeated by (see the module docstring).
        raise NoticeWireError(f"notice text must be a str, got {text!r}")
    if len(text) != NOTICE_TEXT_EXACT_LENGTH:
        # Length first, content second: the refusal a caller is most likely
        # to hit is a longer sentence, and it must not be reported as an
        # encoding problem.
        raise NoticeWireError(
            f"notice text must be exactly {NOTICE_TEXT_EXACT_LENGTH} "
            f"characters ({len(text)} given)"
        )
    if not text.isascii():
        # The pinned evidence is ASCII; the codec would happily encode any
        # UTF-16LE, and a lane that sends Thai here would be claiming a
        # render nobody measured (and the console that reads these logs is
        # cp874 on the bridge machine).
        raise NoticeWireError("notice text must be ASCII")
    if not text.isprintable():
        # `"\x00" * 12` passes `isascii()` and composes a frame of control
        # characters (pf-adversary, round `aa9ajr`, D9).  The measured
        # evidence is printable text; nothing else has been watched render.
        raise NoticeWireError("notice text must be printable")
    if speaker != DEFAULT_SPEAKER or type(speaker) is not str:
        # SPEAKER IS PART OF THE PINNED EVIDENCE, NOT A FREE PARAMETER.
        # Every captured frame on this serializer carries an empty speaker,
        # and pf-adversary (round `aa9ajr`, D9) composed an 8 KB one and a
        # Thai one through the first draft, which type-checked it and
        # nothing else -- an un-pinned half of the very evidence the
        # 12-character body length is pinned by.  A round that needs a
        # speaker moves this line deliberately, with a measurement.
        raise NoticeWireError(
            f"notice speaker must be the measured empty speaker, got {speaker!r}"
        )
    try:
        return make_channel_message_response(
            legacy, LOCAL_TALK_CHANNEL_ID, speaker, text,
        )
    except Exception as exc:  # noqa: BLE001 - see the paragraph below
        # BROADER THAN `make_say_broadcast_frame`'s two-type catch, on
        # purpose.  That one converts `ValueError`/`RuntimeError` because
        # those are what the codec's own checks raise -- but the `legacy`
        # SEAM raises neither: pf-adversary (round `aa9ajr`, D7) passed
        # `None` and a bare object and got `AttributeError` straight through
        # a function whose docstring promises one error type, and a caller
        # writing the obvious `except NoticeWireError` would then meet it as
        # `gm_chat_action_unexpected_AttributeError` on the listener thread.
        # The promise is the contract; this makes it true.
        raise NoticeWireError(
            f"notice rejected by the channel wire codec: {exc}"
        ) from exc


def make_say_broadcast_frame(
    legacy, command: GmCommand, *, speaker: str = DEFAULT_SPEAKER,
) -> tuple[bytes, bytes]:
    """Build a server->client `Channel_GMGlobalMessageVital` frame for a
    parsed `say` command.

    `command` is re-validated here regardless of whether it came from
    `parse_gm_command` -- same policy `gm/warp_executor.py` follows, and for
    the same reason: `docs/GM_LANE.md` commits to accepting a `GmCommand`
    "regardless of source." Every failure surfaces as `SayWireError`, never
    a bare `ValueError`/`TypeError`/`KeyError`/`IndexError`.
    """
    if command.name != "say":
        raise SayWireError(
            f"make_say_broadcast_frame only applies to say commands, got {command.name!r}"
        )
    args = command.args
    if type(args) is not tuple:
        # GmCommand.args is typed tuple[str, ...] (gm/commands.py) -- every
        # legitimate caller, parse_gm_command included, produces a plain
        # tuple. A blacklist of individually-discovered wrong shapes (None,
        # a set, a dict, a str/bytes scalar) is unbounded and was twice
        # defeated by a shape that happened not to raise (a string-keyed
        # dict, then an integer-keyed one). An isinstance(args, tuple)
        # allowlist closed those but was itself defeated by a tuple
        # *subclass* overriding __len__/__getitem__ to raise something
        # other than this module's own error type -- exactly the
        # "regardless of source, hand-built GmCommand" threat model this
        # docstring already claims to defend against, since nothing in
        # GmCommand (a plain frozen dataclass, gm/commands.py) stops a
        # caller from constructing one. Requiring the exact type, not an
        # isinstance match, rejects every subclass outright -- a real tuple
        # can never raise on len()/indexing, so there is no dunder left to
        # lie through.
        raise SayWireError(f"say command args must be a tuple, got {args!r}")
    if len(args) != 1:
        raise SayWireError("say <message> must carry exactly one message argument")
    body = args[0]
    if not isinstance(body, str):
        raise SayWireError(f"say message must be a str, got {body!r}")
    if len(body) > MAX_SAY_MESSAGE_LENGTH:
        raise SayWireError(
            f"say message exceeds {MAX_SAY_MESSAGE_LENGTH} characters "
            f"({len(body)} given)"
        )
    if not isinstance(speaker, str):
        raise SayWireError(f"speaker must be a str, got {speaker!r}")
    try:
        return make_channel_message_response(
            legacy, GM_GLOBAL_CHANNEL_ID, speaker, body,
        )
    except (ValueError, RuntimeError) as exc:
        # `RuntimeError` added round `w8hnu9` after pf-adversary: this clause
        # caught only `ValueError`, but every drift check inside
        # `make_channel_message_response` raises `RuntimeError`
        # (`channel_message_hypothesis.py:547/549/555/570/572` -- composed PC
        # size drift, payload mismatch, re-decode mismatch, pinned-composition
        # drift), so a bare `RuntimeError` could escape a function whose
        # docstring promises every failure surfaces as `SayWireError`.  Not
        # reachable from a typed `/say` today (the pinned checks only fire for
        # the probe bodies), but `gm/chat_command_action._say_action` is the
        # first caller that turns an escape into a wrong event name.
        raise SayWireError(
            f"say command rejected by the channel wire codec: {exc}"
        ) from exc
