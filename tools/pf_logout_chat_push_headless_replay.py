#!/usr/bin/env python3
"""LOGOUT-CHAT-PUSH-001: headless replay for HYP-PF-031 (GT-033 C).

WHAT THIS PROVES, and where the proof stops
-------------------------------------------
That the chat-push logout lane, driven through the REAL make_state_class
dispatcher on a throwaway COPY of the database, answers ONE accepted 34-byte
ascii12 chat-input frame with exactly ONE queued action -- the byte-identical
hash-pinned HYP-PF-028 ReturnSelectServerVital (0x709E) response, pushed
UNSOLICITED with no LogoutVital request pairing -- exactly once (a repeat
trigger is refused by name with zero bytes), commits NOTHING (no table
changes row count, closed_at stays NULL, no socket action, no close timer),
and deliberately leaves a later LogoutVital unanswered with a named event so
the session asks exactly one question.  An independent walker in this file
reads the 0x709E frame back from byte zero (envelope, nested vital id 0x709E
version 0, the 16-byte body: 0x08 u8 = 0, 0x32 8-byte = 0, 0x44 empty
string) WITHOUT importing the module's composer for the read.

It proves NOTHING about a client.  No client has ever been shown an
unsolicited 0x709E push; whether the response ALONE transitions the real
client is GT-033 variant C (attended, not run).  The lane exists because the
attended GT-033 A/B is blocked at the TRIGGER: the tester cannot click the
HOME menu item, so LogoutVital never arrives and the request-paired shapes
can never fire -- but the tester can type into chat, and the chat trigger is
proven end to end by HYP-PF-027.

DISCIPLINE
----------
No server process, no socket, no network, no client, no GameClient window.
The file named by ``--db`` (default ``state/pirateforce.sqlite3``) is read
once to copy it and once to hash it, and is never opened by SQLite for the
session; everything runs on the temporary copy, which is deleted on exit.

Usage:
    py -3 tools/pf_logout_chat_push_headless_replay.py
    py -3 tools/pf_logout_chat_push_headless_replay.py --json
    py -3 tools/pf_logout_chat_push_headless_replay.py --db state/pirateforce.sqlite3

Exit 0 = every wire guard held.  Exit 1 = at least one drifted.  Exit 2 = the
database file named on the command line does not exist.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
# The module under test.  This tool calls its loader and its composer ONCE (to
# build the OTHER side of the byte comparison); it NEVER asks the module to
# decode the dispatched bytes -- the walker below reads them by hand.
from pirateforce_foundation import logout_hypothesis as L  # noqa: E402
from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PROBE_REQUEST_PCS,
    CHAT_INPUT_VITAL_ID,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO = ROOT / "scenarios" / "logout_hypothesis_chat_push_return_select.json"
DEFAULT_DB = ROOT / "state" / "pirateforce.sqlite3"

RUNTIME_PROTOCOL_RES_ID = 0x6E9D
RSS_VITAL_ID = 0x709E
BODY_SIZE = 16
RESP_FRAME_SHA = (
    "08C2A925BD67CD3D0AFA7992F98D472ED8FD22787756521A5DF8CBF174E5CB8E"
)
ACTION_LABEL = "HYP_PF_031_LOGOUT_CHAT_PUSH_RETURN_SELECT_SERVER_UNSOLICITED"


class WalkError(ValueError):
    """The dispatcher emitted something this reader cannot account for."""


def _u16(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 2], "little")


def _u32(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 4], "little")


def walk_return_select_frame(pc: bytes) -> dict:
    """Read the one 0x709E response PC by hand, byte zero to the end."""
    if type(pc) is not bytes or len(pc) < 22:
        raise WalkError("the frame is shorter than the envelope")
    if pc[0] != 0x12 or _u16(pc, 1) != RUNTIME_PROTOCOL_RES_ID:
        raise WalkError("the frame does not open with id 0x6E9D")
    if pc[3] != 0x14 or _u32(pc, 4) != 0:
        raise WalkError("envelope u32 field drift")
    if pc[8] != 0x08 or pc[9] != 4:
        raise WalkError("the envelope is not version 4")
    if pc[10] != 0x0B or pc[11] != 0x02:
        raise WalkError("the outer change mask is not 0x02")
    if pc[12] != 0x12 or _u16(pc, 13) != 1:
        raise WalkError("expected exactly one vital in the collection")
    if pc[15] != 0x12 or _u16(pc, 16) != RSS_VITAL_ID:
        raise WalkError("the nested vital id is not 0x709E")
    if pc[18] != 0x0B or pc[19] != 0x00:
        raise WalkError("the nested vital version is not 0")
    cur = 20
    if pc[cur] != 0x08:
        raise WalkError("field1 tag is not 0x08")
    field1 = pc[cur + 1]
    cur += 2
    if pc[cur] != 0x32:
        raise WalkError("field2 tag is not 0x32")
    field2 = int.from_bytes(pc[cur + 1:cur + 9], "little")
    cur += 9
    if pc[cur] != 0x44:
        raise WalkError("field3 tag is not 0x44")
    strlen = _u32(pc, cur + 1)
    cur += 5
    string = pc[cur:cur + strlen]
    cur += strlen
    # trailing derived-class change mask
    if pc[cur] != 0x0B or pc[cur + 1] != 0x00:
        raise WalkError("the trailing derived-class mask is not 0B 00")
    cur += 2
    if cur != len(pc):
        raise WalkError("the reader accounted for %d of %d bytes"
                        % (cur, len(pc)))
    return {"field1": field1, "field2": field2, "strlen": strlen,
            "string": string}


def table_row_counts(db_path: Path) -> dict:
    db = sqlite3.connect(str(db_path))
    try:
        names = [
            row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            name: db.execute('SELECT COUNT(*) FROM "%s"' % name).fetchone()[0]
            for name in names
        }
    finally:
        db.close()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class _RecordingTimerFactory:
    def __init__(self):
        self.scheduled = []

    def __call__(self, delay_seconds, callback):
        self.scheduled.append((delay_seconds, callback))
        return self


class _RecordingCloser:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1


def main() -> int:
    want_json = "--json" in sys.argv
    db_source = DEFAULT_DB
    if "--db" in sys.argv:
        at = sys.argv.index("--db") + 1
        db_source = Path(sys.argv[at]) if at < len(sys.argv) else DEFAULT_DB
    db_source = db_source.resolve()
    if not db_source.is_file():
        print("no database file at %s" % ascii(str(db_source)))
        return 2

    failures: list[str] = []
    guards = 0

    def check(label, condition, detail=""):
        nonlocal guards
        guards += 1
        if condition:
            if not want_json:
                print("  PASS  %s" % label)
        else:
            failures.append(label)
            if not want_json:
                print("  FAIL  %s %s" % (label, detail))

    legacy = load_legacy(LEGACY_PATH)
    scenario = L.load_logout_hypothesis_scenario(SCENARIO)

    if not want_json:
        print("-- 0. this reader's constants against the module's --")
    check("the vital id and envelope agree with the module",
          RSS_VITAL_ID == L.RETURN_SELECT_SERVER_VITAL_ID
          and BODY_SIZE == L.RETURN_SELECT_SERVER_BODY_SIZE
          and RESP_FRAME_SHA == L.RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256)
    check("the response policy and hypothesis id agree",
          scenario.response_policy
          == L.LOGOUT_RESPONSE_POLICY_CHAT_PUSH_RETURN_SELECT
          and scenario.hypothesis_id == "HYP-PF-031")
    check("the trigger id copy agrees with the proven chat decode",
          L.CHAT_PUSH_TRIGGER_VITAL_ID == CHAT_INPUT_VITAL_ID)
    check("no post-trigger socket action is declared",
          scenario.post_ack_action == L.LOGOUT_POST_ACK_ACTION_NONE
          and scenario.close_delay_ms == 0)

    source_sha_before = sha256_file(db_source)
    tmp = tempfile.mkdtemp(prefix="pf_logout_chat_push001_")
    results: list[dict] = []
    try:
        db_path = Path(tmp) / "logout_chat_push001.sqlite3"
        shutil.copyfile(db_source, db_path)
        if not want_json:
            print("-- 1. a throwaway COPY of the database, and a real session "
                  "on it --")
        check("the copy lives in the temp directory, not at the source",
              db_path.is_file() and db_path.resolve() != db_source)
        check("the copy is byte-identical to the source before any use",
              sha256_file(db_path) == source_sha_before)
        store = SQLiteStore(db_path, ROOT / "migrations")
        check("the store is opened on the copy path ONLY",
              Path(store.path).resolve() == db_path.resolve()
              and Path(store.path).resolve() != db_source)
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
        timer_factory = _RecordingTimerFactory()
        closer = _RecordingCloser()

        state_type = make_state_class(
            legacy, lifecycle, projector,
            logout_hypothesis_scenario=scenario,
            close_timer_factory=timer_factory,
        )
        state = state_type("logout_chat_push")
        state.attach_transport_socket_closer(closer)
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc("logout_chat_push")))
        characters = store.list_characters(state.foundation.account_id)
        if not characters:
            created = state.dispatch(
                legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
            assert created and created[0][0] == "FOUNDATION_CREATE_COMMITTED"
            characters = store.list_characters(state.foundation.account_id)
        start = state.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(characters[-1].selector)))
        assert start and start[0][0] in (
            "FOUNDATION_SELECTED_START_GAME",
            "SCENE2_LOAD_ONLY_SELECTED_START_GAME",
        )
        state.runtime_ack_sent = True
        session_id = state.foundation.session_id

        check("a character is selected on the copy",
              state.foundation.selected is not None)
        check("the runtime-ready sequence flags are set",
              state.teleport_sent is True and state.runtime_ack_sent is True)

        if not want_json:
            print("-- 2. one accepted chat trigger, one unsolicited push --")
        before = table_row_counts(db_path)
        expected_rss = L.make_return_select_server_response(legacy)
        trigger = legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        actions = state.dispatch(trigger)

        check("exactly one action leaves the dispatcher",
              len(actions) == 1, str(len(actions)))
        check("the action carries the HYP-PF-031 push label",
              actions and actions[0][0] == ACTION_LABEL, str(actions[:1]))
        check("the pushed bytes equal the composer's",
              actions and actions[0][1] == expected_rss[0]
              and actions[0][2] == expected_rss[1])
        check("the action took no socket action inline",
              all(len(a) == 4 for a in actions))
        check("the action delay is zero",
              actions and actions[0][3] == 0.0)

        read = None
        error = ""
        try:
            read = walk_return_select_frame(bytes(actions[0][1]))
        except WalkError as exc:
            error = str(exc)
        check("the dispatched 0x709E PC parses by hand",
              read is not None, error)
        if read is not None:
            check("the walked body fields are all zero, string empty",
                  read["field1"] == 0 and read["field2"] == 0
                  and read["strlen"] == 0 and read["string"] == b"")
        check("the dispatched response frame sha matches the pin",
              hashlib.sha256(bytes(actions[0][2])).hexdigest().upper()
              == RESP_FRAME_SHA)
        check("frame == frame_pc(pc) on the dispatched PC",
              bytes(actions[0][2]) == legacy.frame_pc(bytes(actions[0][1])))
        check("the push event is named",
              "logout_chat_push_hypothesis_return_select_pushed"
              in state.events)

        after = table_row_counts(db_path)
        check("NO table changed row count on the push",
              after == before,
              json.dumps({k: (before[k], after[k]) for k in after
                          if before[k] != after[k]}))
        with store.connect() as db:
            row = db.execute("SELECT closed_at FROM sessions WHERE id=?",
                             (session_id,)).fetchone()
        check("closed_at stays NULL: the lease is never touched",
              row is not None and row["closed_at"] is None)
        check("no close timer was scheduled and the closer never ran",
              timer_factory.scheduled == [] and closer.calls == 0)

        if not want_json:
            print("-- 3. the one-shot latch and the one-question rule --")
        again = state.dispatch(trigger)
        check("a repeat trigger is refused with zero bytes",
              again == [])
        check("the repeat refusal is named",
              "logout_chat_push_hypothesis_already_sent_no_reply"
              in state.events)
        for subcode in (1, 3):
            out = state.dispatch(
                legacy.parse_outer(L.LOGOUT_REQUEST_PCS[subcode]))
            check("subcode %02d: LogoutVital under this scenario gets no "
                  "reply" % subcode, out == [])
        check("the LogoutVital refusal is named, twice",
              state.events.count(
                  "logout_chat_push_hypothesis_logout_vital_no_reply") == 2)
        check("no ack and no acknowledged latch after the LogoutVitals",
              state.logout_ack_count == 0
              and state.logout_acknowledged is False)
        check("the push stayed one-shot end to end",
              state.logout_chat_push_count == 1)
        final = table_row_counts(db_path)
        check("NO table changed row count across the whole probe",
              final == before)

        results.append({
            "action_label": actions[0][0],
            "response_frame_sha256":
                hashlib.sha256(bytes(actions[0][2])).hexdigest().upper(),
            "push_count": state.logout_chat_push_count,
        })

        source_sha_after = sha256_file(db_source)
        if not want_json:
            print("-- 4. the source database was never touched --")
        check("the source database sha is unchanged end to end",
              source_sha_after == source_sha_before,
              "%s -> %s" % (source_sha_before, source_sha_after))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if want_json:
        print(json.dumps({
            "guards": guards,
            "failures": failures,
            "results": results,
            "source_sha256": source_sha_before,
        }, indent=2))
    else:
        print()
        print("guards run: %d" % guards)
    if failures:
        if not want_json:
            print("RESULT: FAIL - %d guard(s) drifted: %s"
                  % (len(failures), failures))
        return 1
    if not want_json:
        print("RESULT: PASS - the real dispatcher answers one accepted "
              "ascii12 chat trigger with the pinned unsolicited 0x709E push, "
              "exactly once, writes nothing, takes no socket action, refuses "
              "the repeat and the LogoutVital by name on a throwaway copy, "
              "and leaves the source database untouched (GT-033 variant C is "
              "queued, not run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
