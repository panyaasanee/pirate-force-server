"""LANE-GM's OWN proof that every `/speed` refusal reaches the screen.

COO-DECISION `2026-09-02T03:46+07:00` (`pf_bridge/notes_to_chief/20260902_
0346_COO-DECISION-no-silence-scope-layers-2-4-lane-gm-console-interim-
only.md`), the line addressed to this lane:

    "รอบแรกหลัง PR ของ chief อยู่บน main: ยืนยันในไฟล์รอบว่า **ทั้ง 9 ทางปฏิเสธ**
     ของใบ `0311` ส่ง `SPEED DENIED` (เทสของคุณเอง ไม่รับคำพูดใคร)"

    (first round after chief's PR is on main: confirm in the round file that
     ALL NINE refusal paths of letter `0311` ship `SPEED DENIED` -- YOUR OWN
     TEST, taking nobody's word for it)

WHY THIS FILE EXISTS NEXT TO `tests/test_gm_speed_denied_notice.py`.  That
one is chief's, and it is a good file; this one is not a copy of it and not a
review of it.  The order was to verify the claim WITHOUT standing on the same
footing the claim stands on:

1. IT DECODES THE BYTES WITH ITS OWN PARSER.  `_decode_local_talk_notice`
   below reads the composed PC with the layout written out as literals --
   channel id at `pc[16:18]` little-endian, the nested vital's
   `u8tag(0x0B, version)` at `pc[18:20]`, payload at `pc[20:-2]`, each string
   a `0x48` tag + a 4-byte little-endian BYTE length + UTF-16LE.  It imports
   nothing from `channel_message_hypothesis`, so a day where the project's
   encoder and its own decoder drift TOGETHER (the one failure an
   encode/decode round-trip cannot see) is red here.  The literals come from
   the pinned evidence: `CHAT-ECHO-001/002` for the payload codec, RE-132 and
   `GT-101` for the vital_version byte, `GT-009` for the 12-ASCII render.
2. IT PROVES THE PATHS ARE DISTINCT.  Every path is driven through the real
   `make_gm_chat_command_action` and identified by the word it wrote to the
   AUDIT LOG on disk, not by the event list in memory.  The words are then
   asserted to be that many DIFFERENT words -- so "nine tests are green"
   cannot mean "the same path ran nine times".

WHAT THIS FILE DOES NOT CLAIM.

* `G-OBS`: every byte here is composed in process and asserted in process.
  Nobody has seen `SPEED DENIED` on a screen.  `GT-193` step 9 is the only
  thing that can say that, and until it runs this lane writes "the wire
  carries it", never "the GM sees it".  What is asserted is the action this
  module RETURNS; `runtime.py`'s send site is one layer above and is not
  exercised here.
* EIGHT OF THE NINE ARE REACHABLE FROM A CHAT LINE; THE NINTH IS NOT.
  `commands._require_number` applies `float()` + `math.isfinite` at GRAMMAR
  time and `speed_wire.parse_speed_value` applies the same rule again, so no
  typed value can pass the first and fail the second: path 4 exists as a
  backstop and is reached here only under `mock.patch`.  The refusal a GM is
  most likely to meet in practice -- `/speed fast` -- is refused ABOVE all
  nine, at `parse_gm_command`, and is STILL SILENT ON SCREEN.  chief put that
  gap to COO in letter `0545`; this file does not paper over it.
* THE NINE ARE NINE RETURNS OF ONE FUNCTION, NOT EVERY REFUSAL OF THE
  COMMAND.  `NoRefusalMayGoOutSilentTests` below therefore guards the
  dispatcher branch as well as `_speed_action`'s own returns -- but a refusal
  invented at some third site would still be outside what this file can see.
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import attr_wire  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import speed_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

# ---------------------------------------------------------------------------
# The wire layout, written out rather than imported.  See point 1 above.
# ---------------------------------------------------------------------------
LOCAL_TALK_CHANNEL_ID = 0xAC52
GM_GLOBAL_CHANNEL_ID = 0x9F2C          # the LOCKED channel; never this route
PC_CHANNEL_ID_OFFSET = 16
PC_VITAL_VERSION_OFFSET = 18           # `u8tag(0x0B, version)`
PC_PAYLOAD_OFFSET = 20
PC_TAIL_LENGTH = 2                     # RuntimeRes derived-mask tail
U8_TAG = 0x0B
WSTRING_TAG = 0x48
WSTRING_LENGTH_WIDTH = 4
# RE-132 pinned it and GT-101 measured what a wrong one does to a real
# client: modal error, connection halted, socket closed.  It is OUTSIDE the
# payload, so no amount of payload round-tripping can speak for it -- which
# is exactly why this parser reads it instead of skipping to offset 20.
CHANNEL_CODEC_VITAL_VERSION = 0
NOTICE_BODY = "SPEED DENIED"
NOTICE_BODY_UTF16 = NOTICE_BODY.encode("utf-16-le")   # 24 bytes
NOTICE_SPEAKER = ""

# The refusal words of `pf_bridge/notes_to_chief/20260902_0311_CHIEF-TO-LANE-
# GM-gt193-not-ready-nine-silent-refusal-paths.md`, in the order
# `_speed_action` can reach them.  `<ExcType>` is filled in by the exception
# each path really raises, so three of them are matched by prefix.
#
# 🔴 THE LETTER IS NOT IN THIS REPOSITORY (`pf_bridge` is a different repo and
# the root `.gitignore` is deny-all-with-allowlist), so this tuple is a
# HAND-COPIED pin that cannot be re-derived from its cited source at HEAD.
# `test_every_word_is_an_outcome_constant_this_module_defines` below closes
# half that gap by re-deriving every entry from the module's own
# `OUTCOME_*` constants; the ORDER still rests on the letter.
#
# ~~REFUSAL_PATHS~~ -- renamed, not just extended: GT-193's shape hold made it
# TEN, and a tuple called `NINE` holding ten entries is the drift this file
# exists to catch.  ELEVEN since round `ntf90h`: swapping the write onto
# `store.write_speed_by_identity` gave this route a refusal the composing door
# could not express -- the store said no and the ROW IS UNTOUCHED -- and it is
# a separate word from `refused_speed_persist_` on purpose, because that
# prefix'"'"'s console sentence says the opposite.  The first nine are still letter 0311's, unchanged and in
# its order; the tenth is this lane's own, added in round `et2ux4` after the
# attended round measured what the held shape does to a real client.  It is
# LAST in this tuple but fires FOURTH-AND-A-HALF in the source (between the
# unparseable value and the no-store path) -- the drivers below are numbered
# to match this tuple, and `drivers()` orders by that number, so the pairing
# stays exact; source order is asserted by nothing here and never was.
REFUSAL_PATHS = (
    "withheld_speed_canonical_db",
    "refused_speed_no_selected_character",
    "withheld_update_attr_vital_version",
    "refused_speed_",                    # prefix: unparseable value
    "refused_speed_no_store",
    "refused_speed_no_character_id",
    # prefix: the store raised.  🔴 SINCE ROUND `ntf90h` THIS WORD IS
    # REACHABLE ONLY THROUGH A TEST DOUBLE (pf-adversary, D9): the real
    # `store.write_speed_by_identity` catches `Exception` and returns `None`,
    # so `TypedAttrError`/`KeyError`/`OperationalError`/`AttrComposeError` all
    # arrive as `refused_speed_row_not_touched` instead.  It is kept, and kept
    # tested, because it is what fires if anything ever breaks that door's
    # no-raise contract -- and a reader of this tuple must not take it for a
    # production-reachable word the way the other ten are.
    "refused_speed_persist_",
    "refused_speed_persist_readback_unusable",
    "refused_speed_persist_compose_",    # prefix: post-commit composer
    "withheld_sparse_shape_empty_section",   # GT-193's hold, this lane's own
    "refused_speed_row_not_touched",     # the door refused; the row is intact
)
EXPECTED_PATH_COUNT = len(REFUSAL_PATHS)

# 🔴 THE ELEVENTH NO-BYTES EXIT IS DELIBERATELY NOT IN THE TUPLE ABOVE, and
# saying so is the whole point of this block (pf-adversary, round `hj2cry`,
# D3: an exclusion nobody wrote down is a skip nobody counts).
#
# COO `1847`'s deferral -- `withheld_speed_deferred_login_read` -- is not a
# REFUSAL PATH in this file's sense.  Every entry above goes through
# `_speed_denied` and therefore ships the 12-character `SPEED DENIED` notice
# that letter `0311` and COO-DECISION `0345` are about; the deferral sends
# NOTHING, on purpose, and answers on the console instead.  Adding it here
# would make `test_every_path_prints_both_console_lines` assert a notice frame
# that must not exist.
#
# WHAT THAT COSTS, STATED RATHER THAN HIDDEN: this file's contract now covers
# ten exits and misses THE ONE THE SHIPPED DEFAULT REACHES.  The cover for it
# lives in `tests/test_gm_speed_deferred.py`, which runs against the shipped
# default and pins the console line, its fields, the audit word, the event and
# the undo.  A reader who changes the deferral must go there; a reader who
# adds an eleventh path that DOES notify adds it to the tuple above.
DEFERRAL_IS_NOT_A_NOTICE_PATH = "withheld_speed_deferred_login_read"

# The exits of `_speed_action` that build a `_Verdict` DIRECTLY instead of
# going through `_speed_denied`.  Two since COO-DECISION `20260902_1847`, and
# each one is identified by what it returns rather than by its position:
#   1. the composed command -- an action tuple led by `SPEED_ACTION_LABEL`;
#   2. COO 1847's deferral -- NO action at all (not even the notice), because
#      that decision's own test requirement is "pin that no bytes go out on
#      this route".  It answers on the console instead, and the guard below
#      makes the console half mandatory.
# Raising this number is how a silent refusal would get in, so it is spelled
# here with the reason each exit earns its place.
EXPECTED_BARE_VERDICT_COUNT = 2

CANONICAL_DB_FILENAME = "pirateforce.sqlite3"
RUN_COPY_DB_FILENAME = "pirateforce_lane_gm_20260902_0617.sqlite3"


def make_chat_payload(message: str, speaker: str = "") -> bytes:
    """One inbound 0xAC52 chat payload, in the GT-006/GT-009 measured shape."""
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


def _read_wstring(raw: bytes, at: int) -> tuple[str, int]:
    """One `0x48` + len32LE + UTF-16LE string, and where it ends.

    Deliberately strict about the tag and the length: a composer that started
    emitting a different tag, a character count instead of a byte count, or
    big-endian would still round-trip through the project's own decoder and
    would be caught only here.
    """
    if raw[at] != WSTRING_TAG:
        raise AssertionError(
            "notice string at offset %d has tag 0x%02X, not the measured "
            "0x%02X" % (at, raw[at], WSTRING_TAG)
        )
    start = at + 1 + WSTRING_LENGTH_WIDTH
    length = int.from_bytes(raw[at + 1:start], "little")
    if length % 2:
        raise AssertionError(
            "notice string byte length %d is odd, so it is not UTF-16LE"
            % length
        )
    return raw[start:start + length].decode("utf-16-le"), start + length


def _decode_local_talk_notice(pc: bytes) -> tuple[int, int, str, str]:
    """`(channel_id, vital_version, speaker, body)` read out of a composed PC."""
    channel_id = int.from_bytes(
        pc[PC_CHANNEL_ID_OFFSET:PC_CHANNEL_ID_OFFSET + 2], "little"
    )
    tag, vital_version = pc[
        PC_VITAL_VERSION_OFFSET:PC_VITAL_VERSION_OFFSET + 2
    ]
    if tag != U8_TAG:
        raise AssertionError(
            "the byte before the payload is tag 0x%02X, not the measured "
            "u8 tag 0x%02X -- this is not the frame shape this parser knows"
            % (tag, U8_TAG)
        )
    payload = pc[PC_PAYLOAD_OFFSET:len(pc) - PC_TAIL_LENGTH]
    speaker, after_speaker = _read_wstring(payload, 0)
    body, after_body = _read_wstring(payload, after_speaker)
    if after_body != len(payload):
        raise AssertionError(
            "%d byte(s) left over after the notice body -- the payload is not "
            "the two strings this lane composed" % (len(payload) - after_body)
        )
    return channel_id, vital_version, speaker, body


class FakeSelected:
    def __init__(self, identity_lo=1, identity_hi=0, character_id=1):
        self.identity_lo = identity_lo
        self.identity_hi = identity_hi
        self.id = character_id


class FakeStore:
    """The three methods `_speed_action` and `_speed_undo` reach for.

    `calls` and `stored` are the reason this double is not chief's: a refusal
    that WROTE THE ROW FIRST is still a refusal on screen, and the tests below
    assert per path whether the row moved.  pf-adversary (round `ha492g`, D1)
    moved the canonical-DB gate below the write and every assertion in the
    first draft of this file stayed green with 400.0 sitting in the canonical
    row.
    """

    def __init__(self, path):
        self.path = path
        self.raises = None
        self.readback = None
        self.calls = []
        self.stored = {}

    def read_typed_attributes(self, character_id):
        return dict(self.stored)

    def write_typed_attributes(self, character_id, values):
        self.stored.update(values)

    def write_speed_by_identity(self, identity_lo, identity_hi, speed):
        self.calls.append((identity_lo, identity_hi, speed))
        if self.raises is not None:
            raise self.raises
        if getattr(self, "refuses", False):
            # `None` == the row was NOT touched, so `stored` is left alone.
            return None
        self.stored[chat_command_action.SPEED_TYPED_COLUMN] = speed
        if self.readback is not None:
            return dict(self.readback)
        return {speed_wire.SPEED_FIELD_X: float(speed)}


class StoreWithoutPersistence:
    """A store shape that has a path but no persistence entry point."""

    def __init__(self, path):
        self.path = path
        self.calls = []
        self.stored = {}


class FakeLifecycle:
    def __init__(self, store):
        self.store = store


class FakeFoundation:
    def __init__(self, selected, store):
        self.selected = selected
        self.lifecycle = None if store is None else FakeLifecycle(store)


class FakeSession:
    def __init__(self, store, token="GM_ONE", selected=None):
        self.token = token
        self.events = []
        self.foundation = FakeFoundation(
            FakeSelected() if selected is None else selected, store
        )


class _Case(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"

    def setUp(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.config_path = self.tmp / "gm_accounts.json"
        self.config_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT]}), encoding="utf-8"
        )
        self.log_path = self.tmp / "capture" / "gm_command_log.ndjson"
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

        # GT-193's shape hold sits ABOVE every path this file exercises: with
        # `speed_wire.SHAPES_CLEARED_BY_A_REAL_CLIENT` empty -- the production
        # default, pinned as the default by
        # `tests/test_gm_speed_shape_hold.py` -- `/speed` never reaches the DB
        # write or the composer at all.  These tests are about what happens
        # BELOW that gate, so they clear THIS DOOR'S OWN SIGNATURE explicitly.
        # Doing so here is a TEST-ONLY simulation of a future attended
        # clearance; no client has ever accepted this frame shape.
        _shape_cleared = mock.patch.object(
            speed_wire,
            "SHAPES_CLEARED_BY_A_REAL_CLIENT",
            frozenset({(speed_wire.SECTION_ACTOR_ATTR,)}),
        )
        _shape_cleared.start()
        self.addCleanup(_shape_cleared.stop)
        # AND THE SECOND LOCK, WHICH LANDED ABOVE THAT ONE: COO-DECISION
        # 2026-09-02T18:47+07:00 defers EVERY frame of this door -- whatever
        # its shape -- until LANE-DB lands the `speed_walk` login read on
        # `main` (`speed_wire.send_deferred`).  It sits between the DB write
        # and the shape gate, so without this second patch nothing in this
        # file reaches the composer either.  Also a TEST-ONLY simulation: the
        # shipped default is pinned deferred by
        # `tests/test_gm_speed_deferred.py`, and nothing here is evidence that
        # LANE-DB's login read exists.
        _deferral_lifted = mock.patch.object(
            speed_wire, "SPEED_LOGIN_READ_LANDED", True
        )
        _deferral_lifted.start()
        self.addCleanup(_deferral_lifted.stop)
        # 🔴 ABSOLUTE, AND INSIDE THIS TEST'S OWN TEMP DIRECTORY.  The
        # run-copy gate resolves `os.path.dirname(store.path)` against the
        # PROCESS CWD and fails closed when it cannot ask, so a relative
        # `state/...` path plus a stray `state/pirateforce.sqlite3` in the
        # working directory -- which is `app.py`'s own default, i.e. every
        # machine the server has ever been booted from the repo root, the
        # `GT-193` bridge machine included -- collapsed EIGHT of the nine
        # drivers onto path 1 while their tests stayed green (pf-adversary,
        # round `ha492g`, D2).  An absolute path in a fresh temp directory
        # cannot be influenced by the CWD.
        self.state_dir = self.tmp / "state"
        self.state_dir.mkdir()
        self.run_copy_db = str(self.state_dir / RUN_COPY_DB_FILENAME)
        self.canonical_db = str(self.state_dir / CANONICAL_DB_FILENAME)

    def store(self, path=None):
        return FakeStore(self.run_copy_db if path is None else path)

    def session(self, store=None, selected=None):
        return FakeSession(self.store() if store is None else store,
                           selected=selected)

    def act(self, session, text="/speed 400"):
        return chat_command_action.make_gm_chat_command_action(
            session,
            make_chat_payload(text),
            self.legacy,
            config_path=str(self.config_path),
            log_path=str(self.log_path),
        )

    def audit_outcomes(self):
        """The outcome words this case wrote to the ndjson ON DISK."""
        if not self.log_path.exists():
            return []
        out = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            outcome = json.loads(line).get("outcome")
            if outcome:
                out.append(outcome)
        return out

    # -- the ten drivers, one per path -------------------------------------
    # Each returns `(action, store)`.  They are methods rather than a table of
    # lambdas so a reader can see what makes each path the path it is without
    # following an indirection.  Every one of them keeps its store, because
    # "was the row written?" is half of what a refusal has to answer.

    def path_1_canonical_db(self):
        store = self.store(self.canonical_db)
        return self.act(self.session(store)), store

    def path_2_no_selected_character(self):
        store = self.store()
        session = self.session(store)
        session.foundation.selected = None
        return self.act(session), store

    def path_3_version_gate_shut(self):
        store = self.store()
        with mock.patch.object(
            attr_wire, "UPDATE_ATTR_VITAL_VERSION_CONFIRMED", None
        ):
            return self.act(self.session(store)), store

    def path_4_unparseable_value(self):
        # Patched, not typed -- and that is a statement about production, not
        # about this test: see the docstring's second bullet.
        store = self.store()
        with mock.patch.object(
            speed_wire,
            "parse_speed_value",
            side_effect=speed_wire.SpeedWireError("unparseable"),
        ):
            return self.act(self.session(store), "/speed 5.0"), store

    def path_5_no_store(self):
        store = StoreWithoutPersistence(self.run_copy_db)
        return self.act(self.session(store)), store

    def path_6_no_character_id(self):
        store = self.store()
        selected = FakeSelected()
        selected.id = None
        return self.act(self.session(store, selected=selected)), store

    def path_7_store_raised(self):
        store = self.store()
        store.raises = ValueError("no such column")
        return self.act(self.session(store)), store

    def path_8_readback_unusable(self):
        store = self.store()
        store.readback = {speed_wire.SPEED_FIELD_X: "fast"}
        return self.act(self.session(store)), store

    def path_9_post_commit_compose_failed(self):
        store = self.store()
        with mock.patch.object(
            speed_wire,
            "compose_sparse_speed_update",
            side_effect=ValueError("composer refused"),
        ):
            return self.act(self.session(store)), store

    def path_10_shape_hold_not_cleared(self):
        """The tenth path, and the only one this lane added to its own door.

        `_Case.setUp` clears this door's signature for every test in this
        file, because the other nine paths live below the hold; this driver
        empties the clearance set again, which is the production default
        (`speed_wire.SHAPES_CLEARED_BY_A_REAL_CLIENT` is `frozenset()` on
        `main`).  So this is the one driver that patches a gate BACK to its
        shipped value rather than away from it.
        """
        store = self.store()
        with mock.patch.object(
            speed_wire, "SHAPES_CLEARED_BY_A_REAL_CLIENT", frozenset()
        ):
            return self.act(self.session(store)), store

    def path_11_row_not_touched(self):
        """The eleventh path: LANE-DB'"'"'s door refused and rolled back.

        `None` is that door'"'"'s only failure report, and its contract is that
        every refusal raises INSIDE its transaction -- so unlike path 7 and
        path 9, NOTHING was written here.  The double leaves `stored` alone
        to match.
        """
        store = self.store()
        store.refuses = True
        return self.act(self.session(store)), store

    def drivers(self):
        """The path drivers, ordered by their own number rather than by name.

        `sorted(dir(self))` puts `path_10_*` before `path_1_*`, which would
        misalign every zip in this file for an alignment reason instead of a
        real one (pf-adversary, round `ha492g`, D10).  The numbers are parsed
        and checked to be exactly `1..EXPECTED_PATH_COUNT`.
        """
        found = {}
        for name in dir(self):
            if not name.startswith("path_"):
                continue
            found[int(name.split("_")[1])] = getattr(self, name)
        if sorted(found) != list(range(1, EXPECTED_PATH_COUNT + 1)):
            raise AssertionError(
                "the drivers in this file are numbered %r, not 1..%d"
                % (sorted(found), EXPECTED_PATH_COUNT)
            )
        return [found[n] for n in sorted(found)]

    def assertNoticeCarriesTheMeasuredLine(self, action, path):
        """The action is the `SPEED DENIED` LocalTalk notice, by its bytes."""
        self.assertIsNotNone(
            action,
            "%s returned no action at all, so the serve loop has nothing to "
            "put on this connection -- COO-DECISION 20260902_0345 path 1 "
            "requires the notice on every refusal" % path,
        )
        label, pc, frame, delay = action
        self.assertNotEqual(
            label,
            chat_command_action.SPEED_ACTION_LABEL,
            "%s answered with the COMMAND's own frame: a refused /speed must "
            "never emit an UpdateAttrVital" % path,
        )
        self.assertNotIn(
            "TELEPORT",
            label,
            "%s used a label runtime.py's move-authority grace window keys "
            "off; /speed moves nobody" % path,
        )
        self.assertEqual(delay, 0.0)
        channel_id, vital_version, speaker, body = _decode_local_talk_notice(pc)
        self.assertEqual(
            channel_id,
            LOCAL_TALK_CHANNEL_ID,
            "%s composed on channel 0x%04X. The screen half of COO-DECISION "
            "0147 is 0xAC52 LocalTalk, the one channel GT-009 measured a "
            "render on; 0x%04X GMGlobal in particular is LOCKED by "
            "COO-DECISION 20260829_0041."
            % (path, channel_id, GM_GLOBAL_CHANNEL_ID),
        )
        self.assertEqual(
            vital_version,
            CHANNEL_CODEC_VITAL_VERSION,
            "%s composed vital_version %d. GT-101 measured what an unproven "
            "version does to a real client: modal error, socket closed -- and "
            "this byte lives OUTSIDE the payload, so no encode/decode "
            "round-trip can speak for it." % (path, vital_version),
        )
        self.assertEqual(speaker, NOTICE_SPEAKER)
        self.assertEqual(
            body,
            NOTICE_BODY,
            "%s put %r on the wire, not the exact sentence COO-DECISION "
            "20260902_0345 item 2 pinned" % (path, body),
        )
        self.assertEqual(len(body), 12)
        self.assertTrue(body.isascii())
        self.assertIn(
            NOTICE_BODY_UTF16,
            frame,
            "%s framed a PC whose body bytes are not the 24 UTF-16LE bytes "
            "of the measured sentence" % path,
        )
        self.assertEqual(
            frame[len(frame) - len(pc):],
            pc,
            "%s returned a frame that does not end in the PC that was "
            "decoded, so the decode proves nothing about what would be sent"
            % path,
        )
        return body

    def assertNothingWasWritten(self, store, path):
        self.assertEqual(
            store.calls,
            [],
            "%s refused AFTER calling the persistence method. This is the "
            "shape pf-adversary's D1 mutant had: screen says DENIED, ndjson "
            "says refused, and the row moved anyway." % path,
        )
        self.assertEqual(store.stored, {}, path)


class TheParserItselfIsSoundTests(_Case):
    """The decoder above is only worth what it can be shown to decode.

    A "parser" that happens to fit ONE frame proves nothing about the nine:
    every notice in this file is the same 12-character body, so offsets that
    are really constants tuned to that body would pass every assertion in the
    file.  These compose PCs for other bodies -- through
    `legacy.make_runtime_vitals` with a payload this file encodes ITSELF, so
    the project's channel codec is not in the loop on either side -- and read
    them back.
    """

    def _wstring(self, text):
        raw = text.encode("utf-16-le")
        return bytes([WSTRING_TAG]) + len(raw).to_bytes(
            WSTRING_LENGTH_WIDTH, "little"
        ) + raw

    def _compose(self, body, channel_id=LOCAL_TALK_CHANNEL_ID, speaker="",
                 version=CHANNEL_CODEC_VITAL_VERSION):
        payload = self._wstring(speaker) + self._wstring(body)
        pc, _frame = self.legacy.make_runtime_vitals(
            [(channel_id, version, payload)]
        )
        return pc

    def test_it_reads_bodies_of_every_length_not_just_twelve(self):
        for body in ("A", "0123456789", NOTICE_BODY, "x" * 40):
            with self.subTest(length=len(body)):
                channel_id, version, speaker, decoded = (
                    _decode_local_talk_notice(self._compose(body))
                )
                self.assertEqual(channel_id, LOCAL_TALK_CHANNEL_ID)
                self.assertEqual(version, CHANNEL_CODEC_VITAL_VERSION)
                self.assertEqual(speaker, "")
                self.assertEqual(decoded, body)

    def test_it_reads_the_channel_id_rather_than_assuming_one(self):
        """The mutant that matters: a composer that switched channels.

        If this returned a constant, every channel assertion in this file
        would be a tautology -- which is how a channel swap survived an entire
        green suite once already.
        """
        channel_id, _v, _s, _b = _decode_local_talk_notice(
            self._compose(NOTICE_BODY, channel_id=GM_GLOBAL_CHANNEL_ID)
        )
        self.assertEqual(channel_id, GM_GLOBAL_CHANNEL_ID)

    def test_it_reads_the_vital_version_rather_than_assuming_one(self):
        _c, version, _s, _b = _decode_local_talk_notice(
            self._compose(NOTICE_BODY, version=1)
        )
        self.assertEqual(version, 1)

    def test_it_refuses_a_payload_that_is_not_the_two_strings(self):
        pc = self._compose(NOTICE_BODY)
        with self.assertRaises(AssertionError):
            _decode_local_talk_notice(pc + b"\x00\x00")

    def test_it_refuses_a_different_string_tag(self):
        payload = bytearray(self._wstring("") + self._wstring(NOTICE_BODY))
        payload[0] = 0x49
        pc, _frame = self.legacy.make_runtime_vitals(
            [(LOCAL_TALK_CHANNEL_ID, CHANNEL_CODEC_VITAL_VERSION,
              bytes(payload))]
        )
        with self.assertRaises(AssertionError):
            _decode_local_talk_notice(pc)


class TheNinePathsShipTheLineTests(_Case):
    """One test per refusal path, each asserted on its own bytes.

    Letter `0311` named nine; GT-193's shape hold made it ten (path 10, added
    in round `et2ux4`).  Each test also answers the second half of a refusal:
    did the ROW move?  Paths 1-7 and 10 must not have written anything; paths
    8 and 9 run after the store committed and are pinned that way deliberately
    -- see `WhatARefusalStillCostsTests` at the bottom.
    """

    def test_path_1_canonical_db_withheld(self):
        action, store = self.path_1_canonical_db()
        self.assertNoticeCarriesTheMeasuredLine(action, "path 1 (canonical DB)")
        self.assertNothingWasWritten(store, "path 1 (canonical DB)")

    def test_path_2_no_selected_character(self):
        action, store = self.path_2_no_selected_character()
        self.assertNoticeCarriesTheMeasuredLine(action, "path 2 (no character)")
        self.assertNothingWasWritten(store, "path 2 (no character)")

    def test_path_3_version_gate_shut(self):
        action, store = self.path_3_version_gate_shut()
        self.assertNoticeCarriesTheMeasuredLine(action, "path 3 (version gate)")
        self.assertNothingWasWritten(store, "path 3 (version gate)")

    def test_path_4_unparseable_value(self):
        action, store = self.path_4_unparseable_value()
        self.assertNoticeCarriesTheMeasuredLine(action, "path 4 (bad value)")
        self.assertNothingWasWritten(store, "path 4 (bad value)")

    def test_path_5_no_store(self):
        action, store = self.path_5_no_store()
        self.assertNoticeCarriesTheMeasuredLine(action, "path 5 (no store)")
        self.assertNothingWasWritten(store, "path 5 (no store)")

    def test_path_6_no_character_id(self):
        action, store = self.path_6_no_character_id()
        self.assertNoticeCarriesTheMeasuredLine(action, "path 6 (no char id)")
        self.assertNothingWasWritten(store, "path 6 (no char id)")

    def test_path_7_store_raised(self):
        action, store = self.path_7_store_raised()
        self.assertNoticeCarriesTheMeasuredLine(action, "path 7 (store raised)")
        self.assertEqual(store.stored, {}, "the raising write stored a value")

    def test_path_8_readback_unusable(self):
        action, store = self.path_8_readback_unusable()
        self.assertNoticeCarriesTheMeasuredLine(action, "path 8 (readback)")

    def test_path_9_post_commit_compose_failed(self):
        action, store = self.path_9_post_commit_compose_failed()
        self.assertNoticeCarriesTheMeasuredLine(action, "path 9 (post-commit)")

    def test_path_10_shape_hold_not_cleared(self):
        # The tenth path had no per-path test of its own for one round; it was
        # walked only through `drivers()` (pf-adversary, round `et2ux4`, D9).
        #
        # ~~"It belongs with paths 1-7: nothing may be written."~~ STRUCK: it
        # belongs with paths 8-9 now.  COO-DECISION `20260902_1847` moved the
        # shape hold BELOW the DB write ("the DB write continues as before;
        # what has to stop is the outbound frame, and only that"), so this
        # path refuses with the row already moved -- which is exactly what
        # `assertTheRowMoved` is for and why paths 8 and 9 have always used
        # it.  The screen half is unchanged: the notice still goes out.
        action, store = self.path_10_shape_hold_not_cleared()
        self.assertNoticeCarriesTheMeasuredLine(action, "path 10 (shape hold)")
        self.assertEqual(
            len(store.calls),
            1,
            "path 10 (shape hold) refused without writing the row; COO 1847 "
            "requires the write to continue and only the frame to stop",
        )

    def test_path_11_row_not_touched(self):
        """The eleventh path belongs with paths 1-7: NOTHING may be written.

        And unlike those seven it is the STORE'"'"'s refusal rather than this
        module'"'"'s, which is exactly why the word is its own.
        `store.write_speed_by_identity` raises inside its transaction on
        every refusal, so a `None` back means the row is as it was -- the
        door was called (the row is not written from here without asking)
        and `stored` is untouched.
        """
        action, store = self.path_11_row_not_touched()
        self.assertNoticeCarriesTheMeasuredLine(action, "path 11 (row intact)")
        self.assertEqual(len(store.calls), 1, "the door was never asked")
        self.assertEqual(
            store.stored, {}, "the refusing door left a value in the row"
        )


class TheExcludedEleventhExitTests(_Case):
    """The exclusion above, made a test rather than a comment.

    Without this, `REFUSAL_PATHS` could quietly grow the deferral (and turn
    `test_every_path_prints_both_console_lines` into an assertion about a
    notice that must not exist), or the deferral's word could drift away from
    the constant this file names it by, and nothing here would notice.
    """

    def test_the_deferral_word_is_the_modules_own(self):
        self.assertEqual(
            DEFERRAL_IS_NOT_A_NOTICE_PATH,
            chat_command_action.OUTCOME_SPEED_DEFERRED,
        )

    def test_it_is_not_one_of_the_notice_paths(self):
        self.assertNotIn(DEFERRAL_IS_NOT_A_NOTICE_PATH, REFUSAL_PATHS)
        for path in REFUSAL_PATHS:
            with self.subTest(path=path):
                self.assertFalse(
                    DEFERRAL_IS_NOT_A_NOTICE_PATH.startswith(path),
                    "the deferral matches refusal path %r, so a driver for "
                    "that path could be measuring the deferral instead" % path,
                )


class ThePathsAreDistinctTests(_Case):
    """Nine green tests are worthless if they are one path nine times."""

    def _walk_every_driver(self):
        words = []
        for driver in self.drivers():
            before = len(self.audit_outcomes())
            action, _store = driver()
            self.assertNoticeCarriesTheMeasuredLine(action, driver.__name__)
            written = self.audit_outcomes()[before:]
            self.assertTrue(
                written,
                "%s wrote no outcome row at all, so the audit cannot say "
                "which refusal the GM met" % driver.__name__,
            )
            words.append(written[-1])
        self.assertEqual(len(words), EXPECTED_PATH_COUNT)
        return words

    def test_every_driver_writes_a_distinct_audit_word(self):
        words = self._walk_every_driver()
        self.assertEqual(
            len(set(words)),
            EXPECTED_PATH_COUNT,
            "the drivers produced %d distinct audit words, so at least two of "
            "them walk the SAME refusal: %r" % (len(set(words)), words),
        )

    def test_the_words_are_letter_0311s_own_list(self):
        words = self._walk_every_driver()
        for expected, actual in zip(REFUSAL_PATHS, words):
            self.assertTrue(
                actual.startswith(expected),
                "letter 0311 named %r for this path; the audit says %r"
                % (expected, actual),
            )

    def test_every_word_is_an_outcome_constant_this_module_defines(self):
        """Re-derive the pinned list from the source, since the letter is not
        in this repository (pf-adversary, round `ha492g`, D8)."""
        defined = {
            value
            for name, value in vars(chat_command_action).items()
            if name.startswith("OUTCOME_") and isinstance(value, str)
        }
        for word in REFUSAL_PATHS:
            with self.subTest(word=word):
                self.assertTrue(
                    any(
                        known == word or known.startswith(word)
                        for known in defined
                    ),
                    "%r is in this file's pinned list but is not an OUTCOME_* "
                    "constant of chat_command_action any more" % word,
                )

    def test_every_path_prints_both_console_lines(self):
        """Half (b) of COO-DECISION `0147` AND `GT-193`'s own token.

        This lane's letter `20260902_0419` warned that attaching an action to
        a refusal would delete `GM_CHAT_NO_BYTES_SENT`, because
        `_announce_console_outcome` opens with `if sent: return`.  Chief took
        the `is_notice` fix; this checks it holds on EVERY path, not the one a
        regression test happened to pick.  `GM_CHAT_NOTICE_SENT` is the token
        that tells "the GM saw nothing" apart from "the notice was composed
        then dropped", which for `GT-193` step 9 IS the result.
        """
        drivers = self.drivers()
        self.assertEqual(len(drivers), EXPECTED_PATH_COUNT)
        for driver in drivers:
            with self.subTest(path=driver.__name__):
                stream = io.StringIO()
                with contextlib.redirect_stderr(stream):
                    action, _store = driver()
                self.assertNoticeCarriesTheMeasuredLine(action, driver.__name__)
                printed = stream.getvalue()
                self.assertIn(
                    chat_command_action.WITHHELD_CONSOLE_TOKEN,
                    printed,
                    "%s stopped printing the server-side line; a reader of "
                    "the console can no longer tell this refusal from a "
                    "command that ran" % driver.__name__,
                )
                self.assertIn(
                    chat_command_action.NOTICE_CONSOLE_TOKEN,
                    printed,
                    "%s printed no notice line, so a dropped notice and a "
                    "sent one look identical in the artifact GT-193 step 9 "
                    "is read from" % driver.__name__,
                )

    def test_the_same_twelve_characters_on_every_path(self):
        """One sentence, not nine near-misses.

        COO-DECISION `0345` item 2 pinned ONE string for every path because
        the attended evidence exists at length 12 only.  Nine bodies that each
        decode to something 12 characters long would satisfy every per-path
        assertion above and still be nine different sentences.
        """
        bodies = set()
        for driver in self.drivers():
            action, _store = driver()
            bodies.add(_decode_local_talk_notice(action[1])[3])
        self.assertEqual(bodies, {NOTICE_BODY})


class NoRefusalMayGoOutSilentTests(_Case):
    """The structural half: a TENTH refusal must not be able to ship silent.

    Counting the `_speed_denied` calls proves the paths that exist are wired.
    It cannot prove the next one will be.  These read the source instead, at
    both places a `/speed` verdict can be built:

    * every `return` inside `_speed_action`, INCLUDING a bare `return` and a
      `raise` -- pf-adversary (round `ha492g`, D3) shipped a tenth refusal as
      a bare `return` and the first draft of this file stayed green, with no
      notice, no audit row and no console line at all;
    * the dispatcher branch that calls it, where the sibling `else` already
      builds a `_Verdict(None, ...)` of its own (pf-adversary, D4).
    """

    def _module_tree(self):
        return ast.parse(
            Path(chat_command_action.__file__).read_text(encoding="utf-8")
        )

    def _speed_action_node(self):
        for node in ast.walk(self._module_tree()):
            if isinstance(node, ast.FunctionDef) and node.name == "_speed_action":
                return node
        raise AssertionError("_speed_action is gone from chat_command_action")

    def test_every_return_is_the_notice_or_the_composed_command(self):
        composed = []
        denied = []
        for node in ast.walk(self._speed_action_node()):
            if isinstance(node, ast.Raise):
                raise AssertionError(
                    "_speed_action raises at line %d. The outer handler turns "
                    "that into gm_chat_action_unexpected_* with no action, no "
                    "audit word and no console line -- a refusal more silent "
                    "than the ones COO-DECISION 0345 was written for."
                    % node.lineno
                )
            if not isinstance(node, ast.Return):
                continue
            self.assertIsNotNone(
                node.value,
                "_speed_action has a bare `return` at line %d, which leaves "
                "the caller with None and says nothing anywhere. Every exit "
                "must be `_speed_denied(...)` or the composed verdict."
                % node.lineno,
            )
            call = node.value
            self.assertIsInstance(
                call,
                ast.Call,
                "_speed_action grew a return that is not a call at line %d"
                % node.lineno,
            )
            name = getattr(call.func, "id", None)
            if name == "_speed_denied":
                denied.append(node.lineno)
            elif name == "_Verdict":
                composed.append(node.lineno)
            else:
                raise AssertionError(
                    "_speed_action returns %r at line %d -- neither the "
                    "notice helper nor a verdict" % (name, node.lineno)
                )
        self.assertEqual(
            len(denied),
            EXPECTED_PATH_COUNT,
            "letter 0311 named %d refusal paths; the source has %d going "
            "through the notice helper (lines %r)"
            % (EXPECTED_PATH_COUNT, len(denied), denied),
        )
        self.assertEqual(
            len(composed),
            EXPECTED_BARE_VERDICT_COUNT,
            "_speed_action builds %d verdicts of its own (lines %r). Exactly "
            "%d are allowed: the composed command, and COO 1847's deferral "
            "(which answers on the CONSOLE instead of the screen -- see "
            "`test_the_bare_verdicts_are_the_success_path_and_coo_1847s_"
            "deferral`). Every OTHER refusal goes through `_speed_denied`, or "
            "it goes out silent."
            % (len(composed), composed, EXPECTED_BARE_VERDICT_COUNT),
        )

    def test_the_bare_verdicts_are_the_success_path_and_coo_1847s_deferral(self):
        """The narrowing this file took when COO 1847 landed, said exactly.

        Before that decision every exit of `_speed_action` either sent the
        command or sent the `SPEED DENIED` notice, and this test said "the one
        bare verdict is the success path".  COO `1847` added a SECOND bare
        verdict on purpose: the deferral returns NO action at all, not even
        the notice, because its own test requirement is "pin that no bytes go
        out on this route".

        So the guard is narrowed rather than loosened.  A bare verdict is
        allowed to be exactly one of two things, each identified by what it
        returns, and anything else is still the silent refusal COO `0345`
        closed:

          * the composed command (an action TUPLE led by `SPEED_ACTION_LABEL`);
          * the deferral (action `None`, the audit word
            `OUTCOME_SPEED_DEFERRED`, and a `line_printed=` argument -- silent
            on the screen is only acceptable while it is LOUD on the console).
        """
        found = []
        # ONE parse, reused: `_speed_action_node()` re-parses the module on
        # every call, so nodes from two calls are different objects and an
        # identity test against them silently finds nothing.
        function = self._speed_action_node()
        for node in ast.walk(function):
            if not isinstance(node, ast.Return) or node.value is None:
                continue
            call = node.value
            if getattr(getattr(call, "func", None), "id", None) != "_Verdict":
                continue
            first = call.args[0]
            if isinstance(first, ast.Tuple):
                self.assertEqual(
                    getattr(first.elts[0], "id", None),
                    "SPEED_ACTION_LABEL",
                    "the bare verdict at line %d returns an action tuple that "
                    "is not the composed command" % node.lineno,
                )
                found.append("composed")
                continue
            self.assertIsInstance(
                first,
                ast.Constant,
                "the bare verdict at line %d returns neither an action tuple "
                "nor a literal None, so a refusal may be hiding in it"
                % node.lineno,
            )
            self.assertIsNone(
                first.value,
                "the bare verdict at line %d returns a literal that is not "
                "None" % node.lineno,
            )
            self.assertEqual(
                getattr(call.args[1], "id", None),
                "OUTCOME_SPEED_DEFERRED",
                "the action-less bare verdict at line %d is not COO 1847's "
                "deferral; every other refusal owes the GM a notice and must "
                "go through `_speed_denied`" % node.lineno,
            )
            self.assertIn(
                "line_printed",
                [kw.arg for kw in call.keywords],
                "COO 1847's deferral at line %d sends nothing to the screen, "
                "so it must report whether it reached the CONSOLE -- without "
                "`line_printed` a dead stderr makes it wholly silent"
                % node.lineno,
            )
            found.append("deferred")
            self._assert_the_deferral_branch_holds_one_reason(function, node)
        self.assertEqual(sorted(found), ["composed", "deferred"], found)

    def _assert_the_deferral_branch_holds_one_reason(self, function, return_node):
        """The hole the 1 -> 2 loosening opened, closed (pf-adversary D6).

        The guards above count `Return` nodes and `_Verdict(` spellings, and a
        next-round silent refusal that adds neither is invisible to both: fold
        a second reason into the EXISTING deferral condition --

            if speed_wire.send_deferred() or <anything at all>:

        -- and the whole speed suite stays green.  pf-adversary wrote that
        mutant and measured 276 passed.  Worse than invisible: `send_deferred()`
        is unconditional today, so Python SHORT-CIRCUITS the right-hand side on
        every default-path run.  No test that does not lift the deferral could
        ever observe it, and it would arm itself on the day LANE-DB lands the
        login read -- the exact day the gate above it opens.

        So the condition guarding the action-less verdict must be ONE call and
        nothing else.  A second reason to withhold `/speed` is a refusal of its
        own: it gets its own branch, its own audit word and its own console
        sentence, or it goes through `_speed_denied`.  It does not ride this
        one, whose word names LANE-DB's login read and would then be printed
        for something with nothing to do with it.
        """
        owner = None
        for node in ast.walk(function):
            if isinstance(node, ast.If) and return_node in node.body:
                owner = node
                break
        self.assertIsNotNone(
            owner,
            "the action-less verdict at line %d is not the body of an `if` "
            "any more; this guard cannot see what withholds it"
            % return_node.lineno,
        )
        self.assertIsInstance(
            owner.test,
            ast.Call,
            "the deferral condition at line %d is not a single call -- a "
            "second reason folded in here is a silent refusal wearing COO "
            "1847's audit word (pf-adversary D6)" % owner.lineno,
        )
        self.assertEqual(
            getattr(owner.test.func, "attr", None),
            "send_deferred",
            "the deferral at line %d is guarded by something other than "
            "`speed_wire.send_deferred()`" % owner.lineno,
        )
        self.assertEqual(owner.test.args, [], owner.lineno)

    def test_the_dispatcher_branch_only_calls_speed_action(self):
        """One `def` up, where a refusal is cheapest to add and invisible to
        every assertion above (pf-adversary, round `ha492g`, D4)."""
        branches = []
        for node in ast.walk(self._module_tree()):
            if not isinstance(node, ast.If):
                continue
            test = node.test
            if not isinstance(test, ast.Compare):
                continue
            left = test.left
            if not (
                isinstance(left, ast.Attribute)
                and left.attr == "name"
                and getattr(left.value, "id", None) == "command"
            ):
                continue
            right = test.comparators[0]
            if getattr(right, "value", None) != "speed":
                continue
            branches.append(node)
        self.assertEqual(
            len(branches),
            1,
            "expected exactly one `command.name == \"speed\"` branch in the "
            "dispatcher, found %d" % len(branches),
        )
        body = branches[0].body
        self.assertEqual(
            len(body),
            1,
            "the dispatcher's speed branch grew to %d statement(s). Anything "
            "beyond the single call can build a verdict of its own, and a "
            "`_Verdict(None, ...)` there is a refusal with nothing on screen "
            "that no other test in this file can see." % len(body),
        )
        statement = body[0]
        self.assertIsInstance(statement, ast.Assign)
        self.assertEqual(
            getattr(statement.value.func, "id", None),
            "_speed_action",
            "the dispatcher's speed branch no longer just calls "
            "`_speed_action`",
        )


class WhatARefusalStillCostsTests(_Case):
    """Pinned because it is true, not because it is wanted.

    Paths 8 and 9 run AFTER `store.write_speed_by_identity` committed
    (~~`write_typed_attributes_and_compose_sparse`~~ -- the door swapped in
    round `ntf90h`; what these two paths cost did not), and `_speed_undo` fires only when the AUDIT ROW cannot be
    written -- so the screen says DENIED while the row holds the new value.
    This predates the notice; chief's own pf-adversary pass (round `aa9ajr`,
    D2) found it and reported it rather than changing it, and this lane
    verified it from the source rather than taking the report's word.  If COO
    rules the pairing must change, this test changes with it: that is what
    pinning it is for.
    """

    def test_paths_8_and_9_say_denied_with_the_row_already_moved(self):
        for driver in (
            self.path_8_readback_unusable,
            self.path_9_post_commit_compose_failed,
        ):
            with self.subTest(path=driver.__name__):
                action, store = driver()
                self.assertNoticeCarriesTheMeasuredLine(action, driver.__name__)
                self.assertEqual(
                    len(store.calls),
                    1,
                    "%s no longer writes before it refuses; if that is "
                    "deliberate, this pin is what should be deleted"
                    % driver.__name__,
                )
                self.assertIn(
                    chat_command_action.SPEED_TYPED_COLUMN,
                    store.stored,
                    "%s refused and the row did NOT move -- better than what "
                    "this pins, so re-read the paragraph above before "
                    "'fixing' this test" % driver.__name__,
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
